"""
=============================================================================
 CLASIFICADOR DE RESIDUOS — TRAMPILLA INTELIGENTE
 ClasificadorGUI  |  Tkinter + OpenCV + TensorFlow + PySerial
 Clases detectadas: "Aluminio"  y  "Plástico"
=============================================================================
 Dependencias:
   pip install opencv-python tensorflow pyserial numpy Pillow
=============================================================================
"""

# ── Suprimir mensajes de TensorFlow antes de cualquier importación ─────────
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "2"

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import queue
import cv2
import numpy as np
from PIL import Image, ImageTk

# ── PySerial (opcional) ────────────────────────────────────────────────────
try:
    import serial
    import serial.tools.list_ports
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False

# ── TensorFlow (opcional) ──────────────────────────────────────────────────
try:
    import tensorflow as tf
    TF_OK = True
except ImportError:
    TF_OK = False


# =============================================================================
#  CONSTANTES
# =============================================================================
CLASS_NAMES      = ["Aluminio", "Plástico"]
INPUT_SIZE       = (224, 224)
COOLDOWN_SEG     = 2.5    # segundos entre detecciones confirmadas
MIN_AREA         = 3000   # área mínima de contorno (px²)
HITS_CONFIRM     = 5      # frames consecutivos para confirmar objeto
FRAME_BUF        = 2      # tamaño de cola de frames

CLASS_COLORS = {
    "Aluminio":    (0, 200, 255),
    "Plástico":    (0, 255, 80),
    "Desconocido": (160, 160, 160),
}

# =============================================================================
#  PALETA DE COLORES DE LA GUI
# =============================================================================
BG        = "#0d1117"
PANEL_BG  = "#161b22"
BORDER    = "#30363d"
ACCENT    = "#58a6ff"
GREEN     = "#3fb950"
RED       = "#f85149"
YELLOW    = "#d29922"
DARK_BTN  = "#21262d"
TEXT_MAIN = "#e6edf3"
TEXT_DIM  = "#8b949e"

FONT_TITLE = ("Consolas", 11, "bold")
FONT_LABEL = ("Consolas", 9)
FONT_VALUE = ("Consolas", 22, "bold")
FONT_BTN   = ("Consolas", 9, "bold")
FONT_SMALL = ("Consolas", 8)


# =============================================================================
#  HILO DE VISIÓN E INFERENCIA
# =============================================================================
class VisionThread(threading.Thread):
    """
    Captura frames, detecta objetos y realiza inferencia. Corre como daemon.

    Modos de detección (en orden de prioridad):
      1. SSDLite (.tflite) — detector de cajas, luego clasificador Keras sobre ROI
      2. MOG2 + contornos  — fallback si no hay modelo SSD cargado
    """

    def __init__(self, cam_index, model_path, ssd_path,
                 frame_q, event_q, conf_var, stop_evt):
        super().__init__(daemon=True)
        self.cam_index  = cam_index
        self.model_path = model_path   # .keras / .h5  → clasificador
        self.ssd_path   = ssd_path     # .tflite       → detector (opcional)
        self.frame_q    = frame_q
        self.event_q    = event_q
        self.conf_var   = conf_var
        self.stop_evt   = stop_evt

        self.model      = None         # modelo Keras
        self.ssd        = None         # intérprete TFLite
        self.ssd_input  = None         # detalle del tensor de entrada SSD
        self.ssd_size   = (300, 300)   # resolución de entrada SSD por defecto

    # =========================================================================
    #  CARGA DE MODELOS
    # =========================================================================
    def _load_classifier(self):
        """Carga el clasificador Keras (.keras / .h5)."""
        if not TF_OK or not self.model_path:
            return
        try:
            gpus = tf.config.list_physical_devices("GPU")
            if gpus:
                tf.config.experimental.set_memory_growth(gpus[0], True)
            self.model = tf.keras.models.load_model(self.model_path)
            print(f"[OK] Clasificador: {os.path.basename(self.model_path)}")
        except Exception as exc:
            print(f"[ERROR] Clasificador: {exc}")

    def _load_ssd(self):
        """
        Carga el detector SSDLite (.tflite).
        Detecta automáticamente el tamaño de entrada y el tipo de dato.
        """
        if not TF_OK or not self.ssd_path:
            return
        try:
            interp = tf.lite.Interpreter(model_path=self.ssd_path)
            interp.allocate_tensors()

            inp         = interp.get_input_details()[0]
            h           = inp["shape"][1]
            w           = inp["shape"][2]
            self.ssd_size  = (w, h)
            self.ssd_input = inp
            self.ssd       = interp
            print(f"[OK] SSD detector: {os.path.basename(self.ssd_path)}"
                  f"  entrada={w}x{h}  dtype={inp['dtype'].__name__}")
        except Exception as exc:
            print(f"[ERROR] SSD: {exc}")

    # =========================================================================
    #  DETECCIÓN  —  SSDLite TFLite
    # =========================================================================
    def _detect_ssd(self, frame_bgr):
        """
        Corre inferencia con el modelo SSDLite.
        Devuelve la mejor caja (x1, y1, x2, y2) en coordenadas de píxel,
        o None si no hay detección por encima del umbral mínimo SSD (0.3).

        Formato de salida estándar TF OD API (4 tensores):
          [0] boxes      → shape (1, N, 4)  [ymin, xmin, ymax, xmax] normalizados
          [1] classes    → shape (1, N)
          [2] scores     → shape (1, N)
          [3] num_dets   → shape (1,)
        """
        h_f, w_f = frame_bgr.shape[:2]
        w_in, h_in = self.ssd_size

        # Preprocesar al tamaño y dtype del modelo
        img = cv2.resize(frame_bgr, (w_in, h_in))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        dtype = self.ssd_input["dtype"]
        if dtype == np.uint8:
            tensor = img.astype(np.uint8)
        else:
            tensor = (img / 255.0).astype(np.float32)
        tensor = np.expand_dims(tensor, axis=0)

        self.ssd.set_tensor(self.ssd_input["index"], tensor)
        self.ssd.invoke()

        out_details = self.ssd.get_output_details()

        # Ordenar salidas por índice para seguir la convención TF OD API
        out_details_sorted = sorted(out_details, key=lambda d: d["index"])

        if len(out_details_sorted) < 3:
            return None   # formato desconocido

        boxes  = self.ssd.get_tensor(out_details_sorted[0]["index"])[0]
        scores = self.ssd.get_tensor(out_details_sorted[2]["index"])[0]

        # Filtrar: score mínimo fijo en 0.3 (independiente del slider)
        SSD_MIN_SCORE = 0.30
        best_score = -1.0
        best_box   = None

        for i, score in enumerate(scores):
            if score > SSD_MIN_SCORE and score > best_score:
                best_score = score
                best_box   = boxes[i]   # [ymin, xmin, ymax, xmax] normalizado

        if best_box is None:
            return None

        ymin, xmin, ymax, xmax = best_box
        x1 = max(0,   int(xmin * w_f))
        y1 = max(0,   int(ymin * h_f))
        x2 = min(w_f, int(xmax * w_f))
        y2 = min(h_f, int(ymax * h_f))

        # Rechazar cajas demasiado pequeñas
        if (x2 - x1) * (y2 - y1) < MIN_AREA:
            return None

        return x1, y1, x2, y2

    # =========================================================================
    #  DETECCIÓN  —  MOG2 + contornos (fallback)
    # =========================================================================
    def _detect_mog2(self, frame_bgr, bg_sub, kernel):
        """Devuelve la mejor caja (x1, y1, x2, y2) o None."""
        mask = bg_sub.apply(frame_bgr)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.dilate(mask, kernel, iterations=2)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        best_cnt, best_area = None, 0
        for cnt in contours:
            a = cv2.contourArea(cnt)
            if a > MIN_AREA and a > best_area:
                best_cnt, best_area = cnt, a

        if best_cnt is None:
            return None

        x, y, w, h = cv2.boundingRect(best_cnt)
        x1 = max(0,               x)
        y1 = max(0,               y)
        x2 = min(frame_bgr.shape[1], x + w)
        y2 = min(frame_bgr.shape[0], y + h)
        return x1, y1, x2, y2

    # =========================================================================
    #  CLASIFICACIÓN  —  Keras
    # =========================================================================
    def _preprocess(self, roi_bgr):
        img = cv2.resize(roi_bgr, INPUT_SIZE)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        return np.expand_dims(img, axis=0)

    def _classify(self, roi_bgr):
        """Devuelve (etiqueta, confianza) o ('Desconocido', 0)."""
        if self.model is None:
            return "Desconocido", 0.0
        preds = self.model.predict(self._preprocess(roi_bgr), verbose=0)[0]
        if len(preds) == 1:                      # sigmoid
            conf = float(preds[0])
            return (CLASS_NAMES[1], conf) if conf >= 0.5 \
                   else (CLASS_NAMES[0], 1.0 - conf)
        else:                                     # softmax
            idx  = int(np.argmax(preds))
            conf = float(preds[idx])
            lbl  = CLASS_NAMES[idx] if idx < len(CLASS_NAMES) else "Desconocido"
            return lbl, conf

    # =========================================================================
    #  DIBUJO
    # =========================================================================
    def _draw_box(self, frame, x1, y1, x2, y2, label, conf, mode_tag):
        color    = CLASS_COLORS.get(label, (160, 160, 160))
        tag_text = f"{label}  {conf*100:.1f}%  [{mode_tag}]"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.60, 2)
        cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 8, y1), color, -1)
        cv2.putText(frame, tag_text, (x1 + 4, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (20, 20, 20), 2)

    # =========================================================================
    #  BUCLE PRINCIPAL
    # =========================================================================
    def run(self):
        self._load_classifier()
        self._load_ssd()

        cap = cv2.VideoCapture(self.cam_index)
        if not cap.isOpened():
            self.event_q.put(("error", "No se pudo abrir la cámara."))
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Fallback MOG2 (siempre se inicializa, solo se usa si no hay SSD)
        bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=40, detectShadows=False
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

        # Notificar modo activo
        mode = "SSD" if self.ssd is not None else "MOG2"
        self.event_q.put(("info", f"Detector activo: {mode}"))

        last_time   = 0.0
        last_label  = None
        consec_hits = 0

        while not self.stop_evt.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.04)
                continue

            display   = frame.copy()
            threshold = self.conf_var.get() / 100.0
            now       = time.time()

            # ── Detección ─────────────────────────────────────────────────
            if self.ssd is not None:
                box      = self._detect_ssd(frame)
                mode_tag = "SSD"
            else:
                box      = self._detect_mog2(frame, bg_sub, kernel)
                mode_tag = "MOG2"

            det_label, det_conf = None, 0.0

            if box is not None:
                x1, y1, x2, y2 = box
                roi = frame[y1:y2, x1:x2]

                label, conf = ("Desconocido", 0.0)
                if roi.size > 0:
                    label, conf = self._classify(roi)

                self._draw_box(display, x1, y1, x2, y2, label, conf, mode_tag)

                if conf >= threshold and label != "Desconocido":
                    det_label, det_conf = label, conf

            # ── Cooldown + confirmación ────────────────────────────────────
            if det_label:
                if det_label == last_label:
                    consec_hits += 1
                else:
                    consec_hits, last_label = 1, det_label

                if consec_hits >= HITS_CONFIRM and now - last_time >= COOLDOWN_SEG:
                    last_time   = now
                    consec_hits = 0
                    self.event_q.put(("detection", det_label, det_conf))
            else:
                consec_hits = 0

            # ── Overlay de estado ──────────────────────────────────────────
            cd_rest = max(0.0, COOLDOWN_SEG - (now - last_time))
            cv2.putText(
                display,
                f"Umbral:{self.conf_var.get():.0f}%  CD:{cd_rest:.1f}s  [{mode_tag}]",
                (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (210, 210, 210), 1
            )

            # ── Enviar frame a GUI ─────────────────────────────────────────
            try:
                self.frame_q.put_nowait(display)
            except queue.Full:
                pass

        cap.release()


# =============================================================================
#  CLASE PRINCIPAL DE LA GUI
# =============================================================================
class ClasificadorGUI:
    """Interfaz gráfica principal del clasificador de residuos."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Clasificador de Residuos IA")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.minsize(960, 640)

        # ── Variables de estado ───────────────────────────────────────────
        self.model_path     = tk.StringVar(value="(ningún modelo seleccionado)")
        self.ssd_path       = tk.StringVar(value="(opcional — sin SSD)")
        self.cam_index      = tk.IntVar(value=0)
        self.port_var       = tk.StringVar(value="")
        self.conf_var       = tk.DoubleVar(value=70.0)
        self.count_alu      = tk.IntVar(value=0)
        self.count_plas     = tk.IntVar(value=0)

        self.serial_conn    = None
        self.vision_thread  = None
        self.stop_evt       = threading.Event()
        self.frame_q        = queue.Queue(maxsize=FRAME_BUF)
        self.event_q        = queue.Queue()
        self._cam_running   = False

        # ── Construir UI por secciones ────────────────────────────────────
        self._apply_combobox_style()
        self._build_layout()
        self._build_video_panel()
        self._build_side_panel()

        self._refresh_ports()
        self._poll()          # arrancar ciclo de actualización

    # =========================================================================
    #  ESTILOS
    # =========================================================================
    def _apply_combobox_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TCombobox",
            fieldbackground=DARK_BTN, background=DARK_BTN,
            foreground=TEXT_MAIN, selectbackground=DARK_BTN,
            selectforeground=TEXT_MAIN, bordercolor=BORDER,
            arrowcolor=ACCENT)

    # =========================================================================
    #  LAYOUT PRINCIPAL  (grid: col 0 = video expandible, col 1 = panel fijo)
    # =========================================================================
    def _build_layout(self):
        self._main = tk.Frame(self.root, bg=BG)
        self._main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._main.columnconfigure(0, weight=1)   # video se estira
        self._main.columnconfigure(1, weight=0)   # panel lateral fijo
        self._main.rowconfigure(0, weight=1)

    # =========================================================================
    #  PANEL DE VIDEO (col 0)
    # =========================================================================
    def _build_video_panel(self):
        vf = tk.Frame(self._main, bg=PANEL_BG,
                      highlightbackground=BORDER, highlightthickness=1)
        vf.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        vf.rowconfigure(2, weight=1)
        vf.columnconfigure(0, weight=1)

        tk.Label(vf, text="◉  FEED EN VIVO",
                 bg=PANEL_BG, fg=ACCENT, font=FONT_TITLE,
                 anchor="w", padx=10).grid(row=0, column=0,
                                           sticky="ew", pady=(6, 2))
        tk.Frame(vf, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew")

        self.canvas = tk.Label(
            vf, bg="#0a0a0a",
            text="Cámara no iniciada\n\nSelecciona modelo → Iniciar Cámara",
            fg=TEXT_DIM, font=FONT_LABEL, justify=tk.CENTER
        )
        self.canvas.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)

    # =========================================================================
    #  PANEL LATERAL (col 1, ancho fijo 300 px)
    # =========================================================================
    def _build_side_panel(self):
        # ── Contenedor exterior (fijo 300 px) ────────────────────────────
        outer = tk.Frame(self._main, bg=PANEL_BG, width=300,
                         highlightbackground=BORDER, highlightthickness=1)
        outer.grid(row=0, column=1, sticky="nsew")
        outer.pack_propagate(False)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        # ── Canvas desplazable ────────────────────────────────────────────
        self._side_canvas = tk.Canvas(
            outer, bg=PANEL_BG, highlightthickness=0, bd=0
        )
        self._side_canvas.grid(row=0, column=0, sticky="nsew")

        # ── Barra de desplazamiento ───────────────────────────────────────
        vsb = tk.Scrollbar(
            outer, orient=tk.VERTICAL,
            command=self._side_canvas.yview,
            bg=DARK_BTN, troughcolor=PANEL_BG,
            activebackground=ACCENT, relief=tk.FLAT
        )
        vsb.grid(row=0, column=1, sticky="ns")
        self._side_canvas.configure(yscrollcommand=vsb.set)

        # ── Frame interior (contenido real) ───────────────────────────────
        self._side = tk.Frame(self._side_canvas, bg=PANEL_BG)
        self._side_window = self._side_canvas.create_window(
            (0, 0), window=self._side, anchor="nw"
        )

        # Actualizar región desplazable cuando cambie el tamaño interior
        self._side.bind("<Configure>", self._on_side_configure)
        # Ajustar ancho del frame interior al canvas
        self._side_canvas.bind("<Configure>", self._on_canvas_configure)

        # Scroll con rueda del ratón
        self._side_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._build_section_model()
        self._build_section_camera()
        self._build_section_serial()
        self._build_section_threshold()
        self._build_section_stats()
        self._build_section_log()

    # ── Callbacks de scroll ───────────────────────────────────────────────
    def _on_side_configure(self, event):
        """Actualiza la región desplazable cuando el contenido cambia de tamaño."""
        self._side_canvas.configure(
            scrollregion=self._side_canvas.bbox("all")
        )

    def _on_canvas_configure(self, event):
        """Mantiene el frame interior con el mismo ancho que el canvas."""
        self._side_canvas.itemconfig(self._side_window, width=event.width)

    def _on_mousewheel(self, event):
        """Desplaza el panel lateral con la rueda del ratón."""
        self._side_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Helpers reutilizables ─────────────────────────────────────────────
    def _section_title(self, text):
        """Título de sección con separador debajo."""
        tk.Label(self._side, text=text,
                 bg=PANEL_BG, fg=ACCENT, font=FONT_TITLE,
                 anchor="w", padx=10
                 ).pack(fill=tk.X, pady=(10, 2))
        tk.Frame(self._side, bg=BORDER, height=1).pack(fill=tk.X, padx=10)

    def _row(self):
        """Frame contenedor para una fila del panel."""
        f = tk.Frame(self._side, bg=PANEL_BG)
        f.pack(fill=tk.X, padx=10, pady=3)
        return f

    def _btn(self, parent, text, cmd, color=ACCENT):
        return tk.Button(
            parent, text=text, command=cmd,
            bg=DARK_BTN, fg=color, font=FONT_BTN,
            activebackground="#30363d", activeforeground=color,
            relief=tk.FLAT, cursor="hand2", padx=8, pady=4,
            highlightthickness=1, highlightbackground=BORDER
        )

    # =========================================================================
    #  SECCIÓN 1 — MODELO
    # =========================================================================
    def _build_section_model(self):
        self._section_title("①  MODELOS DE IA")

        # ── Clasificador Keras ────────────────────────────────────────────
        tk.Label(self._side, text="Clasificador (.keras / .h5)",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_SMALL,
                 anchor="w", padx=12).pack(fill=tk.X, pady=(4, 0))

        r = self._row()
        self._btn(r, "  Buscar clasificador", self._select_model, ACCENT
                  ).pack(fill=tk.X)

        self._lbl_model = tk.Label(
            self._side, textvariable=self.model_path,
            bg=PANEL_BG, fg=TEXT_DIM, font=FONT_SMALL,
            wraplength=265, anchor="w", padx=12
        )
        self._lbl_model.pack(fill=tk.X, pady=(0, 2))

        # ── Separador interno ─────────────────────────────────────────────
        tk.Frame(self._side, bg=BORDER, height=1
                 ).pack(fill=tk.X, padx=10, pady=(4, 0))

        # ── Detector SSDLite ──────────────────────────────────────────────
        r_ssd = tk.Frame(self._side, bg=PANEL_BG)
        r_ssd.pack(fill=tk.X, padx=12, pady=(4, 0))

        tk.Label(r_ssd, text="Detector SSDLite (.tflite)",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_SMALL,
                 anchor="w").pack(side=tk.LEFT)

        # Badge que indica si SSD está cargado
        self._lbl_ssd_badge = tk.Label(
            r_ssd, text="OFF", bg="#2d1f0e", fg=TEXT_DIM,
            font=("Consolas", 7, "bold"), padx=4
        )
        self._lbl_ssd_badge.pack(side=tk.RIGHT)

        r = self._row()
        self._btn(r, "  Buscar modelo SSD", self._select_ssd, YELLOW
                  ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._btn(r, "✖", self._clear_ssd, RED
                  ).pack(side=tk.LEFT, padx=(4, 0))

        self._lbl_ssd = tk.Label(
            self._side, textvariable=self.ssd_path,
            bg=PANEL_BG, fg=TEXT_DIM, font=FONT_SMALL,
            wraplength=265, anchor="w", padx=12
        )
        self._lbl_ssd.pack(fill=tk.X, pady=(0, 2))

        # Nota informativa
        tk.Label(
            self._side,
            text="Sin SSD → usa MOG2 (sustracción de fondo)",
            bg=PANEL_BG, fg="#444d56", font=("Consolas", 7),
            anchor="w", padx=12
        ).pack(fill=tk.X, pady=(0, 4))

    # =========================================================================
    #  SECCIÓN 2 — CÁMARA
    # =========================================================================
    def _build_section_camera(self):
        self._section_title("②  CÁMARA")

        r = self._row()
        tk.Label(r, text="Índice:", bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_LABEL, width=8, anchor="w").pack(side=tk.LEFT)
        ttk.Combobox(r, textvariable=self.cam_index,
                     values=[0, 1, 2, 3], width=5,
                     state="readonly").pack(side=tk.LEFT, padx=4)

        r = self._row()
        self._btn_cam = self._btn(r, "▶  Iniciar Cámara",
                                  self._toggle_camera, GREEN)
        self._btn_cam.pack(fill=tk.X)

    # =========================================================================
    #  SECCIÓN 3 — SERIAL
    # =========================================================================
    def _build_section_serial(self):
        self._section_title("③  ARDUINO — SERIAL")

        r = self._row()
        tk.Label(r, text="Puerto:", bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_LABEL, width=8, anchor="w").pack(side=tk.LEFT)
        self._port_cb = ttk.Combobox(r, textvariable=self.port_var,
                                     values=[], width=11, state="readonly")
        self._port_cb.pack(side=tk.LEFT, padx=4)
        self._btn(r, "↺", self._refresh_ports, TEXT_DIM
                  ).pack(side=tk.LEFT, padx=2)

        r = self._row()
        self._btn_ser = self._btn(r, "⚡  Conectar Arduino",
                                  self._toggle_serial, YELLOW)
        self._btn_ser.pack(fill=tk.X)

        r = self._row()
        self._lbl_ser = tk.Label(r, text="● Desconectado",
                                 bg=PANEL_BG, fg=RED, font=FONT_SMALL,
                                 anchor="w")
        self._lbl_ser.pack(fill=tk.X)

    # =========================================================================
    #  SECCIÓN 4 — UMBRAL DE CONFIANZA
    # =========================================================================
    def _build_section_threshold(self):
        self._section_title("④  UMBRAL DE CONFIANZA")

        r = self._row()
        self._lbl_conf = tk.Label(r, text="70 %",
                                  bg=PANEL_BG, fg=ACCENT,
                                  font=("Consolas", 16, "bold"), width=6)
        self._lbl_conf.pack(side=tk.RIGHT)

        self._scale = tk.Scale(
            self._side, from_=0, to=100,
            orient=tk.HORIZONTAL, variable=self.conf_var,
            command=self._on_conf_change,
            bg=PANEL_BG, fg=TEXT_MAIN, troughcolor=DARK_BTN,
            highlightthickness=0, sliderrelief=tk.FLAT,
            activebackground=ACCENT, font=FONT_SMALL,
            showvalue=False, length=240
        )
        self._scale.pack(fill=tk.X, padx=10)

        r = self._row()
        tk.Label(r, text="0 %",   bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side=tk.LEFT)
        tk.Label(r, text="100 %", bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side=tk.RIGHT)

    # =========================================================================
    #  SECCIÓN 5 — ESTADÍSTICAS
    # =========================================================================
    def _build_section_stats(self):
        self._section_title("⑤  ESTADÍSTICAS")

        sf = tk.Frame(self._side, bg=PANEL_BG)
        sf.pack(fill=tk.X, padx=10, pady=6)
        sf.columnconfigure(0, weight=1)
        sf.columnconfigure(1, weight=1)

        # Tarjeta Aluminio
        ca = tk.Frame(sf, bg="#0d1f2d",
                      highlightbackground="#00c8ff", highlightthickness=1)
        ca.grid(row=0, column=0, padx=(0, 4), sticky="nsew")
        tk.Label(ca, text="Aluminio", bg="#0d1f2d",
                 fg="#00c8ff", font=FONT_SMALL).pack(pady=(6, 0))
        tk.Label(ca, textvariable=self.count_alu, bg="#0d1f2d",
                 fg="#00c8ff", font=FONT_VALUE).pack()
        tk.Label(ca, text="detectados", bg="#0d1f2d",
                 fg=TEXT_DIM, font=FONT_SMALL).pack(pady=(0, 6))

        # Tarjeta Plástico
        cp = tk.Frame(sf, bg="#0d2d1a",
                      highlightbackground=GREEN, highlightthickness=1)
        cp.grid(row=0, column=1, padx=(4, 0), sticky="nsew")
        tk.Label(cp, text="Plástico", bg="#0d2d1a",
                 fg=GREEN, font=FONT_SMALL).pack(pady=(6, 0))
        tk.Label(cp, textvariable=self.count_plas, bg="#0d2d1a",
                 fg=GREEN, font=FONT_VALUE).pack()
        tk.Label(cp, text="detectados", bg="#0d2d1a",
                 fg=TEXT_DIM, font=FONT_SMALL).pack(pady=(0, 6))

        r = self._row()
        self._btn(r, "🗑  Resetear Contadores",
                  self._reset_counters, RED).pack(fill=tk.X)

    # =========================================================================
    #  SECCIÓN 6 — LOG
    # =========================================================================
    def _build_section_log(self):
        self._section_title("⑥  LOG DE EVENTOS")

        lf = tk.Frame(self._side, bg=PANEL_BG)
        lf.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))

        sb = tk.Scrollbar(lf, bg=PANEL_BG, troughcolor=PANEL_BG)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._log_box = tk.Text(
            lf, bg="#0a0e14", fg=TEXT_DIM, font=FONT_SMALL,
            height=7, state=tk.DISABLED, relief=tk.FLAT, wrap=tk.WORD,
            highlightbackground=BORDER, highlightthickness=1,
            yscrollcommand=sb.set
        )
        self._log_box.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self._log_box.yview)

        self._log_box.tag_configure("alu",    foreground="#00c8ff")
        self._log_box.tag_configure("plas",   foreground=GREEN)
        self._log_box.tag_configure("err",    foreground=RED)
        self._log_box.tag_configure("serial", foreground=YELLOW)
        self._log_box.tag_configure("info",   foreground=TEXT_DIM)

        self._log("Sistema iniciado.", "info")

    # =========================================================================
    #  LÓGICA — MODELO
    # =========================================================================
    def _select_model(self):
        path = filedialog.askopenfilename(
            title="Seleccionar clasificador",
            filetypes=[("Modelos Keras", "*.keras *.h5"),
                       ("Todos", "*.*")]
        )
        if path:
            self.model_path.set(path)
            self._log(f"Clasificador: {os.path.basename(path)}", "info")

    def _select_ssd(self):
        path = filedialog.askopenfilename(
            title="Seleccionar detector SSDLite (.tflite)",
            filetypes=[("TFLite", "*.tflite"),
                       ("Todos", "*.*")]
        )
        if path:
            self.ssd_path.set(path)
            self._lbl_ssd_badge.configure(
                text=" SSD ", bg="#1f3d1f", fg=GREEN
            )
            self._log(f"SSD detector: {os.path.basename(path)}", "info")

    def _clear_ssd(self):
        self.ssd_path.set("(opcional — sin SSD)")
        self._lbl_ssd_badge.configure(text="OFF", bg="#2d1f0e", fg=TEXT_DIM)
        self._log("SSD detector removido → se usará MOG2.", "info")

    # =========================================================================
    #  LÓGICA — CÁMARA
    # =========================================================================
    def _toggle_camera(self):
        if self._cam_running:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        mp = self.model_path.get()
        if mp == "(ningún modelo seleccionado)":
            if not messagebox.askyesno(
                "Sin modelo",
                "No se ha seleccionado un modelo .keras/.h5.\n"
                "¿Continuar solo con visualización?"
            ):
                return
            mp = ""

        self.stop_evt.clear()
        self._clear_queues()

        # Resolver rutas (vaciar si son los valores por defecto)
        mp  = mp if mp else ""
        ssd = self.ssd_path.get()
        ssd = ssd if (ssd and not ssd.startswith("(")) else ""

        self.vision_thread = VisionThread(
            cam_index  = self.cam_index.get(),
            model_path = mp,
            ssd_path   = ssd,
            frame_q    = self.frame_q,
            event_q    = self.event_q,
            conf_var   = self.conf_var,
            stop_evt   = self.stop_evt
        )
        self.vision_thread.start()
        self._cam_running = True
        self._btn_cam.configure(text="■  Detener Cámara", fg=RED)
        self._log(f"Cámara {self.cam_index.get()} iniciada.", "info")

    def _stop_camera(self):
        self.stop_evt.set()
        self._cam_running = False
        self._btn_cam.configure(text="▶  Iniciar Cámara", fg=GREEN)
        self.canvas.configure(image="",
                              text="Cámara detenida.", fg=TEXT_DIM)
        self._log("Cámara detenida.", "info")

    def _clear_queues(self):
        for q in (self.frame_q, self.event_q):
            while not q.empty():
                try: q.get_nowait()
                except queue.Empty: break

    # =========================================================================
    #  LÓGICA — SERIAL
    # =========================================================================
    def _refresh_ports(self):
        if not SERIAL_OK:
            self._port_cb.configure(values=["(pyserial no instalado)"])
            return
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self._port_cb.configure(values=ports or ["(sin puertos)"])
        if ports:
            self.port_var.set(ports[0])
        self._log(f"Puertos: {ports or 'ninguno'}", "info")

    def _toggle_serial(self):
        if self.serial_conn and self.serial_conn.is_open:
            self._disconnect_serial()
        else:
            self._connect_serial()

    def _connect_serial(self):
        if not SERIAL_OK:
            messagebox.showerror("Error", "pyserial no instalado.")
            return
        port = self.port_var.get()
        if not port or port.startswith("("):
            messagebox.showwarning("Advertencia",
                                   "Selecciona un puerto COM válido.")
            return
        try:
            self.serial_conn = serial.Serial(port, baudrate=9600, timeout=1)
            self._lbl_ser.configure(text=f"● Conectado  {port}", fg=GREEN)
            self._btn_ser.configure(text="✖  Desconectar Arduino")
            self._log(f"Serial: {port} @ 9600", "serial")
        except Exception as exc:
            messagebox.showerror("Error Serial", str(exc))
            self._log(f"Error serial: {exc}", "err")

    def _disconnect_serial(self):
        if self.serial_conn:
            try: self.serial_conn.close()
            except Exception: pass
        self.serial_conn = None
        self._lbl_ser.configure(text="● Desconectado", fg=RED)
        self._btn_ser.configure(text="⚡  Conectar Arduino")
        self._log("Serial desconectado.", "serial")

    def _send_serial(self, char: str):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(char.encode("ascii"))
                self._log(f"TX → '{char}'", "serial")
            except Exception as exc:
                self._log(f"Error TX: {exc}", "err")

    # =========================================================================
    #  LÓGICA — UMBRAL Y CONTADORES
    # =========================================================================
    def _on_conf_change(self, value):
        self._lbl_conf.configure(text=f"{float(value):.0f} %")

    def _reset_counters(self):
        self.count_alu.set(0)
        self.count_plas.set(0)
        self._log("Contadores reseteados.", "info")

    # =========================================================================
    #  LOG HELPER
    # =========================================================================
    def _log(self, msg: str, tag: str = "info"):
        ts = time.strftime("%H:%M:%S")
        self._log_box.configure(state=tk.NORMAL)
        self._log_box.insert(tk.END, f"[{ts}] {msg}\n", tag)
        self._log_box.see(tk.END)
        self._log_box.configure(state=tk.DISABLED)

    # =========================================================================
    #  CICLO DE POLLING (hilo principal, no bloqueante)
    # =========================================================================
    def _poll(self):
        self._poll_frames()
        self._poll_events()
        self.root.after(30, self._poll)

    def _poll_frames(self):
        """Toma el frame más reciente de la cola y actualiza el canvas."""
        latest = None
        try:
            while True:
                latest = self.frame_q.get_nowait()
        except queue.Empty:
            pass

        if latest is None:
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw > 10 and ch > 10:
            latest = cv2.resize(latest, (cw, ch),
                                interpolation=cv2.INTER_LINEAR)

        img = Image.fromarray(cv2.cvtColor(latest, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(image=img)
        self.canvas.configure(image=photo, text="")
        self.canvas._ref = photo          # evitar garbage collection

    def _poll_events(self):
        """Procesa detecciones confirmadas y errores del hilo de visión."""
        try:
            while True:
                ev = self.event_q.get_nowait()

                if ev[0] == "detection":
                    _, label, conf = ev
                    if label == "Aluminio":
                        self.count_alu.set(self.count_alu.get() + 1)
                        self._send_serial("A")
                        self._log(
                            f"✔ ALUMINIO  {conf*100:.1f}%  "
                            f"[total: {self.count_alu.get()}]", "alu")
                    elif label == "Plástico":
                        self.count_plas.set(self.count_plas.get() + 1)
                        self._send_serial("P")
                        self._log(
                            f"✔ PLÁSTICO  {conf*100:.1f}%  "
                            f"[total: {self.count_plas.get()}]", "plas")

                elif ev[0] == "info":
                    self._log(ev[1], "info")

                elif ev[0] == "error":
                    messagebox.showerror("Error de cámara", ev[1])
                    self._log(f"Error: {ev[1]}", "err")
                    self._stop_camera()

        except queue.Empty:
            pass

    # =========================================================================
    #  CIERRE LIMPIO
    # =========================================================================
    def on_close(self):
        self.stop_evt.set()
        self._disconnect_serial()
        if self.vision_thread and self.vision_thread.is_alive():
            self.vision_thread.join(timeout=2.0)
        self.root.destroy()


# =============================================================================
#  PUNTO DE ENTRADA
# =============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app  = ClasificadorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    # Centrar en pantalla
    W, H = 1100, 700
    root.update_idletasks()
    sx = (root.winfo_screenwidth()  - W) // 2
    sy = (root.winfo_screenheight() - H) // 2
    root.geometry(f"{W}x{H}+{sx}+{sy}")

    root.mainloop()