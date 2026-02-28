import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, scrolledtext
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector, Cursor
from matplotlib.animation import FuncAnimation
import os
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class SpectrometerViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Análisis de Semiconductores - Essick (1993) & Gordillo (2003) [CORREGIDO]")
        self.root.geometry("1900x1000")
        self.root.minsize(1700, 900)

        # Variables
        self.spectra_data = []
        self.colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'gray', 'olive', 'cyan']
        self.current_tool = None
        self.selected_spectrum_idx = None
        self.markers = {}
        self.marker_artists = []
        self.audit_log = []
        self.tauc_figures = []
        self.animation_running = False
        self.current_animation = None
        
        # Para selección de región
        self.rect_selector = None
        self.region_start_point = None

        # Configurar estilo
        self.root.configure(bg='#f0f0f0')
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 9, 'bold'))
        style.configure('Tauc.TButton', font=('Arial', 9, 'bold'), foreground='blue')
        style.configure('Help.TButton', font=('Arial', 9, 'bold'), foreground='green')

        # Crear interfaz
        self.create_widgets()

    def create_widgets(self):
        # Panel principal
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo (controles + ayuda)
        left_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(left_paned, weight=1)

        left_frame = ttk.Frame(left_paned, padding="5", width=350)
        left_frame.pack_propagate(False)
        left_paned.add(left_frame, weight=3)

        help_frame = ttk.LabelFrame(left_paned, text="📖 Guía Rápida de Herramientas", padding="5")
        left_paned.add(help_frame, weight=1)
        self.create_help_panel(help_frame)

        # Panel central (gráfica principal)
        center_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(center_paned, weight=3)

        # Gráfica principal
        plot_frame = ttk.LabelFrame(center_paned, text="Espectro de Transmitancia - CLICK Y ARRASTRA para seleccionar regiones", padding="5")
        center_paned.add(plot_frame, weight=3)
        
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Longitud de onda (nm)")
        self.ax.set_ylabel("Transmitancia")
        self.ax.set_title("Espectro de Transmitancia")
        self.ax.grid(True, alpha=0.3)

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.pack(fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

        # Cursor
        self.cursor = Cursor(self.ax, useblit=True, color='red', linewidth=1)

        # Controles de animación
        anim_frame = ttk.LabelFrame(center_paned, text="🎬 Controles de Animación Tauc", padding="5")
        center_paned.add(anim_frame, weight=0)
        
        anim_controls = ttk.Frame(anim_frame)
        anim_controls.pack(fill=tk.X)
        ttk.Button(anim_controls, text="▶️ Play Directo", command=lambda: self.animate_tauc_fit('direct')).pack(side=tk.LEFT, padx=2)
        ttk.Button(anim_controls, text="▶️ Play Indirecto", command=lambda: self.animate_tauc_fit('indirect')).pack(side=tk.LEFT, padx=2)
        ttk.Button(anim_controls, text="⏹️ Stop", command=self.stop_animation).pack(side=tk.LEFT, padx=2)
        
        self.anim_status = ttk.Label(anim_frame, text="Listo", foreground='blue')
        self.anim_status.pack(pady=2)

        # Resultados y valores en punto
        bottom_frame = ttk.Frame(center_paned)
        center_paned.add(bottom_frame, weight=1)
        
        quick_frame = ttk.LabelFrame(bottom_frame, text="Resultados del Análisis", padding="5")
        quick_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.quick_results_text = tk.Text(quick_frame, height=10, font=('Courier', 9), wrap=tk.WORD)
        self.quick_results_text.pack(fill=tk.BOTH, expand=True)

        point_frame = ttk.LabelFrame(bottom_frame, text="Valores en Punto (mover mouse)", padding="5", width=350)
        point_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        point_frame.pack_propagate(False)
        self.point_values_text = tk.Text(point_frame, height=10, font=('Courier', 9), wrap=tk.WORD, bg='#fffff0')
        self.point_values_text.pack(fill=tk.BOTH, expand=True)

        # Conectar eventos del mouse
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)

        # Panel derecho (auditoría)
        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=2)

        audit_frame = ttk.LabelFrame(right_paned, text="Auditoría de Cálculos", padding="5")
        right_paned.add(audit_frame, weight=2)
        
        control_audit = ttk.Frame(audit_frame)
        control_audit.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_audit, text="🔄 Actualizar", command=self.refresh_audit).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_audit, text="🗑️ Limpiar", command=self.clear_audit).pack(side=tk.LEFT, padx=2)

        columns = ('variable', 'formula', 'values', 'result', 'status')
        self.audit_tree = ttk.Treeview(audit_frame, columns=columns, show='tree headings', height=15)
        self.audit_tree.heading('#0', text='Paso')
        self.audit_tree.heading('variable', text='Variable')
        self.audit_tree.heading('formula', text='Fórmula')
        self.audit_tree.heading('values', text='Valores')
        self.audit_tree.heading('result', text='Resultado')
        self.audit_tree.heading('status', text='Estado')
        self.audit_tree.column('#0', width=120)
        self.audit_tree.column('variable', width=80)
        self.audit_tree.column('formula', width=180)
        self.audit_tree.column('values', width=150)
        self.audit_tree.column('result', width=100)
        self.audit_tree.column('status', width=60)

        vsb = ttk.Scrollbar(audit_frame, orient="vertical", command=self.audit_tree.yview)
        hsb = ttk.Scrollbar(audit_frame, orient="horizontal", command=self.audit_tree.xview)
        self.audit_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.audit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        log_frame = ttk.LabelFrame(right_paned, text="Log de Operaciones", padding="5")
        right_paned.add(log_frame, weight=1)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=('Courier', 8), height=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Panel extremo derecho (Tauc + herramientas)
        far_right = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(far_right, weight=1)

        tauc_frame = ttk.LabelFrame(far_right, text="Gráficas Tauc", padding="5")
        far_right.add(tauc_frame, weight=2)
        
        ttk.Button(tauc_frame, text="📈 Directo (αhν)²", 
                  command=lambda: self.plot_tauc('direct')).pack(fill=tk.X, pady=2)
        ttk.Button(tauc_frame, text="📉 Indirecto √α", 
                  command=lambda: self.plot_tauc('indirect')).pack(fill=tk.X, pady=2)
        ttk.Button(tauc_frame, text="📉 Urbach ln(α)", 
                  command=lambda: self.plot_tauc('urbach')).pack(fill=tk.X, pady=2)
        
        ttk.Separator(tauc_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        ttk.Label(tauc_frame, text="Herramientas Manuales:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        tools_inner = ttk.Frame(tauc_frame)
        tools_inner.pack(fill=tk.X, pady=2)
        ttk.Button(tools_inner, text="🔴 Punto Inflexión", command=self.activate_inflection_tool).pack(fill=tk.X, pady=1)
        ttk.Button(tools_inner, text="🟦 Región 1 (pre-gap)", command=self.activate_region1_tool).pack(fill=tk.X, pady=1)
        ttk.Button(tools_inner, text="🟩 Región 2 (post-gap)", command=self.activate_region2_tool).pack(fill=tk.X, pady=1)
        ttk.Button(tools_inner, text="⭐ Centro del Canto", command=self.activate_edge_center_tool).pack(fill=tk.X, pady=1)
        ttk.Button(tools_inner, text="🔻 Mínimos Interf.", command=self.activate_minima_tool).pack(fill=tk.X, pady=1)
        ttk.Button(tools_inner, text="❌ Borrar Todo", command=self.clear_markers_current).pack(fill=tk.X, pady=1)

        # Panel de estado de herramienta
        self.tool_status_label = ttk.Label(far_right, text="Herramienta: Ninguna", 
                                          font=('Arial', 10, 'bold'), foreground='blue')
        self.tool_status_label.pack(pady=5)

        instr_frame = ttk.LabelFrame(far_right, text="Instrucciones Paso a Paso", padding="5")
        far_right.add(instr_frame, weight=1)
        self.instr_text = scrolledtext.ScrolledText(instr_frame, wrap=tk.WORD, font=('Arial', 9), height=10)
        self.instr_text.pack(fill=tk.BOTH, expand=True)
        self.update_instructions("Bienvenido. Cargue un archivo para comenzar.")

        # Barra de estado
        self.root.statusbar = tk.Label(self.root, text="Listo", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.root.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Controles en left_frame
        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_files = ttk.Frame(notebook)
        notebook.add(tab_files, text="📁 Archivos")
        self.create_files_tab(tab_files)

        tab_plot = ttk.Frame(notebook)
        notebook.add(tab_plot, text="📊 Gráfica")
        self.create_plot_settings_tab(tab_plot)

        tab_analysis = ttk.Frame(notebook)
        notebook.add(tab_analysis, text="🔬 Análisis")
        self.create_analysis_tab(tab_analysis)

    def create_help_panel(self, parent):
        help_text = """
🎯 PASOS BÁSICOS:

1. CARGAR: Botón "Agregar archivos .sp"

2. SELECCIONAR: Click en lista de archivos

3. CONFIGURAR tipo y espesor

4. Para REGIONES: Click en botón 🟦 o 🟩,
   luego CLICK Y ARRASTRA en la gráfica

5. Soltar para confirmar la selección

📍 HERRAMIENTAS:

🔴 Punto Inflexión: Click único
🟦 Región 1: Click y arrastra (pre-gap)
🟩 Región 2: Click y arrastra (post-gap)
⭐ Centro Canto: Click único
🔻 Mínimos: Click en 2+ mínimos
        """
        text_widget = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=('Courier', 9), height=15)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(1.0, help_text)
        text_widget.config(state=tk.DISABLED)

    def update_instructions(self, message):
        self.instr_text.delete(1.0, tk.END)
        self.instr_text.insert(1.0, f"[{datetime.now().strftime('%H:%M:%S')}]\n{message}\n")

    def set_tool_status(self, tool_name, color='blue'):
        self.tool_status_label.config(text=f"Herramienta activa: {tool_name}", foreground=color)

    # ========== SISTEMA DE SELECCIÓN DE REGIÓN CORREGIDO ==========

    def on_mouse_press(self, event):
        """Maneja el click inicial del mouse"""
        if event.inaxes != self.ax or self.selected_spectrum_idx is None:
            return
        
        # Si estamos en modo región, iniciar selección
        if self.current_tool in ['region1', 'region2']:
            self.region_start_point = (event.xdata, event.ydata)
            self.log_message(f"Iniciando selección de {self.current_tool} en x={event.xdata:.1f}")
        elif self.current_tool in ['inflection', 'edge_center', 'minima']:
            # Herramientas de click único
            self.handle_single_click(event.xdata, event.ydata)

    def on_mouse_move(self, event):
        """Maneja el movimiento del mouse - muestra valores y dibuja preview de región"""
        # Actualizar valores en punto
        if event.inaxes == self.ax and self.selected_spectrum_idx is not None:
            self.update_point_values(event.xdata)
        
        # Dibujar preview de región si estamos arrastrando
        if self.current_tool in ['region1', 'region2'] and self.region_start_point is not None and event.inaxes == self.ax:
            self.draw_region_preview(self.region_start_point[0], event.xdata)

    def on_mouse_release(self, event):
        """Maneja el release del mouse - finaliza selección de región"""
        if event.inaxes != self.ax or self.selected_spectrum_idx is None:
            return
        
        if self.current_tool in ['region1', 'region2'] and self.region_start_point is not None:
            x1 = self.region_start_point[0]
            x2 = event.xdata
            
            # Asegurar que x1 < x2
            if x1 > x2:
                x1, x2 = x2, x1
            
            # Guardar la región
            idx = self.selected_spectrum_idx
            if self.current_tool == 'region1':
                self.markers[idx]['region1'] = (x1, x2)
                region_name = "Región 1 (pre-gap)"
                color = "blue"
            else:
                self.markers[idx]['region2'] = (x1, x2)
                region_name = "Región 2 (post-gap)"
                color = "green"
            
            # Limpiar preview y dibujar definitivo
            self.region_start_point = None
            if hasattr(self, 'preview_patch'):
                self.preview_patch.remove()
                delattr(self, 'preview_patch')
            
            self.redraw_markers()
            self.finish_tool(f"{region_name} seleccionada: {x1:.0f} - {x2:.0f} nm")
            
            self.add_to_audit(f"Selección {region_name}", "λ_range", f"{x1:.0f}-{x2:.0f}nm", 
                            f"Δλ={x2-x1:.0f}nm", f"ΔE={abs(1239.84/x1-1239.84/x2):.3f}eV", "OK")

    def draw_region_preview(self, x1, x2):
        """Dibuja un preview de la región mientras se arrastra"""
        # Eliminar preview anterior
        if hasattr(self, 'preview_patch'):
            self.preview_patch.remove()
        
        # Crear nuevo preview
        y_min, y_max = self.ax.get_ylim()
        color = 'blue' if self.current_tool == 'region1' else 'green'
        
        self.preview_patch = self.ax.axvspan(x1, x2, alpha=0.3, color=color, linestyle='--', edgecolor='black')
        self.canvas.draw_idle()

    def handle_single_click(self, x, y):
        """Maneja herramientas de click único"""
        idx = self.selected_spectrum_idx
        
        if self.current_tool == 'inflection':
            self.markers[idx]['inflection'] = (x, y)
            E_val = 1239.84 / x
            self.add_to_audit("Marcado manual", "E_infl", "1239.84/λ", 
                            f"λ={x:.2f}nm", f"{E_val:.3f}eV", "✓ OK")
            self.finish_tool(f"Punto de inflexión marcado en λ={x:.1f}nm, E={E_val:.3f}eV")
            
        elif self.current_tool == 'edge_center':
            self.markers[idx]['edge_center'] = (x, y)
            E_val = 1239.84 / x
            self.add_to_audit("Centro canto", "E_center", "1239.84/λ", 
                            f"λ={x:.2f}nm", f"{E_val:.3f}eV", "✓ OK")
            self.finish_tool(f"Centro del canto marcado en λ={x:.1f}nm, E={E_val:.3f}eV")
            
        elif self.current_tool == 'minima':
            if 'minima' not in self.markers[idx]:
                self.markers[idx]['minima'] = []
            self.markers[idx]['minima'].append((x, y))
            n_minima = len(self.markers[idx]['minima'])
            self.redraw_markers()
            self.update_instructions(f"Mínimo {n_minima} marcado en λ={x:.1f}nm\n"
                                   f"Necesita {2-n_minima} más para calcular espesor.")
            if n_minima >= 2:
                self.calc_n_from_minima()
                self.finish_tool("Mínimos completados - espesor calculado")

    def finish_tool(self, message):
        """Finaliza el uso de una herramienta"""
        self.current_tool = None
        self.canvas.get_tk_widget().config(cursor="arrow")
        self.set_tool_status("Ninguna", "gray")
        self.log_message(message)
        self.update_instructions(f"✅ {message}\n\nSeleccione otra herramienta o ejecute el análisis.")

    # ========== ACTIVACIÓN DE HERRAMIENTAS ==========

    def activate_inflection_tool(self):
        self.current_tool = 'inflection'
        self.canvas.get_tk_widget().config(cursor="cross")
        self.set_tool_status("Punto de Inflexión (click único)", "red")
        self.update_instructions(
            "🔴 HERRAMIENTA: Punto de Inflexión\n\n"
            "INSTRUCCIONES:\n"
            "1. Localice el borde de absorción (donde T cae bruscamente)\n"
            "2. Haga CLICK en el punto de máxima pendiente\n"
            "3. No arrastre, solo un click\n\n"
            "Este punto marca el cambio más rápido en la absorción."
        )

    def activate_region1_tool(self):
        self.current_tool = 'region1'
        self.canvas.get_tk_widget().config(cursor="cross")
        self.set_tool_status("Región 1 (click y arrastre)", "blue")
        self.region_start_point = None
        self.update_instructions(
            "🟦 HERRAMIENTA: Región 1 (Pre-gap)\n\n"
            "INSTRUCCIONES:\n"
            "1. PRESIONE el botón del mouse en el inicio de la región\n"
            "2. ARRASTRE hasta el final de la región deseada\n"
            "3. SUELTE para confirmar\n\n"
            "Para gap indirecto: seleccione zona lineal ANTES del canto.\n"
            "Verá un área azul mientras arrastra."
        )

    def activate_region2_tool(self):
        self.current_tool = 'region2'
        self.canvas.get_tk_widget().config(cursor="cross")
        self.set_tool_status("Región 2 (click y arrastre)", "green")
        self.region_start_point = None
        self.update_instructions(
            "🟩 HERRAMIENTA: Región 2 (Post-gap)\n\n"
            "INSTRUCCIONES:\n"
            "1. PRESIONE el botón del mouse en el inicio de la región\n"
            "2. ARRASTRE hasta el final de la región deseada\n"
            "3. SUELTE para confirmar\n\n"
            "Para gap indirecto: seleccione zona lineal DESPUÉS del canto.\n"
            "Verá un área verde mientras arrastra."
        )

    def activate_edge_center_tool(self):
        self.current_tool = 'edge_center'
        self.canvas.get_tk_widget().config(cursor="cross")
        self.set_tool_status("Centro del Canto (click único)", "orange")
        self.update_instructions(
            "⭐ HERRAMIENTA: Centro del Canto de Absorción\n\n"
            "INSTRUCCIONES:\n"
            "1. Localice el centro del borde de absorción\n"
            "2. Haga CLICK en ese punto (punto medio entre T alta y baja)\n"
            "3. No arrastre, solo un click\n\n"
            "Este punto sirve como referencia visual del gap estimado."
        )

    def activate_minima_tool(self):
        self.current_tool = 'minima'
        self.canvas.get_tk_widget().config(cursor="cross")
        self.set_tool_status("Mínimos de Interferencia (2+ clicks)", "purple")
        self.update_instructions(
            "🔻 HERRAMIENTA: Mínimos de Interferencia\n\n"
            "INSTRUCCIONES:\n"
            "1. Haga CLICK en el primer mínimo (valle)\n"
            "2. Haga CLICK en el segundo mínimo\n"
            "3. Puede añadir más si lo desea\n\n"
            "Use esta herramienta para películas delgadas con franjas de interferencia."
        )

    # ========== MÉTODOS DE DIBUJO ==========

    def redraw_markers(self):
        """Redibuja todos los marcadores"""
        # Limpiar artistas anteriores
        if hasattr(self, 'marker_artists'):
            for art in self.marker_artists:
                if art in self.ax.patches or art in self.ax.lines or art in self.ax.collections:
                    art.remove()
        self.marker_artists = []
        
        for idx, marks in self.markers.items():
            if idx >= len(self.spectra_data) or not self.spectra_data[idx]['visible']:
                continue
            
            # Punto de inflexión
            if marks.get('inflection'):
                x, y = marks['inflection']
                art = self.ax.plot(x, y, 'o', markersize=12, color='red', 
                                 markeredgecolor='darkred', markeredgewidth=2, zorder=5)[0]
                self.marker_artists.append(art)
                art = self.ax.axvline(x, color='red', linestyle='--', alpha=0.5, linewidth=1.5, zorder=4)
                self.marker_artists.append(art)
                ann = self.ax.annotate('Inflex', xy=(x, y), xytext=(10, 10), 
                                     textcoords='offset points', fontsize=9, color='red', fontweight='bold')
                self.marker_artists.append(ann)
            
            # Centro del canto
            if marks.get('edge_center'):
                x, y = marks['edge_center']
                art = self.ax.plot(x, y, '*', markersize=20, color='gold', 
                                 markeredgecolor='orange', markeredgewidth=2, zorder=5)[0]
                self.marker_artists.append(art)
                art = self.ax.axvline(x, color='gold', linestyle='-', alpha=0.8, linewidth=2.5, zorder=4)
                self.marker_artists.append(art)
                E_center = 1239.84 / x
                ann = self.ax.annotate(f'Centro\nEg≈{E_center:.2f}eV', xy=(x, y), 
                                     xytext=(10, -30), textcoords='offset points', 
                                     fontsize=9, color='darkgoldenrod', fontweight='bold',
                                     bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))
                self.marker_artists.append(ann)
            
            # Región 1
            if marks.get('region1'):
                x1, x2 = marks['region1']
                art = self.ax.axvspan(x1, x2, alpha=0.25, color='blue', zorder=3)
                self.marker_artists.append(art)
                ann = self.ax.annotate('R1 (pre-gap)', xy=((x1+x2)/2, self.ax.get_ylim()[1]*0.95), 
                                     fontsize=10, color='blue', ha='center', fontweight='bold')
                self.marker_artists.append(ann)
            
            # Región 2
            if marks.get('region2'):
                x1, x2 = marks['region2']
                art = self.ax.axvspan(x1, x2, alpha=0.25, color='green', zorder=3)
                self.marker_artists.append(art)
                ann = self.ax.annotate('R2 (post-gap)', xy=((x1+x2)/2, self.ax.get_ylim()[1]*0.90), 
                                     fontsize=10, color='green', ha='center', fontweight='bold')
                self.marker_artists.append(ann)
            
            # Mínimos de interferencia
            for i, (x, y) in enumerate(marks.get('minima', [])):
                art = self.ax.plot(x, y, 'v', markersize=10, color='purple', 
                                 markeredgecolor='black', markeredgewidth=1.5, zorder=5)[0]
                self.marker_artists.append(art)
                ann = self.ax.annotate(f'm{i+1}', xy=(x, y), xytext=(0, 12), 
                                     textcoords='offset points', fontsize=9, color='purple', fontweight='bold')
                self.marker_artists.append(ann)
        
        self.canvas.draw()

    # ========== MÉTODOS DE CÁLCULO Y ANÁLISIS ==========

    def calculate_alpha_bulk_essick(self, T, R, d_cm, audit_parent=None):
        """Cálculo de α según Essick 1993 Eq. 9"""
        T = np.clip(T, 1e-10, 1.0)
        R = np.clip(R, 0.0, 0.999)
        
        # Ecuación cuadrática: R²T x² + (1-R)² x - T = 0
        a = R**2 * T
        b = (1 - R)**2
        c = -T
        
        discriminant = b**2 - 4*a*c
        alpha = np.zeros_like(T)
        
        mask_valid = discriminant >= 0
        if np.any(mask_valid):
            x = (-b + np.sqrt(discriminant[mask_valid])) / (2*a[mask_valid])
            x = np.clip(x, 1e-10, 1.0)
            alpha[mask_valid] = -np.log(x) / d_cm
        
        if np.any(~mask_valid):
            alpha[~mask_valid] = -np.log(T[~mask_valid] / (1-R)**2) / d_cm
        
        return np.maximum(alpha, 0)

    def calc_thickness_from_interference(self):
        """Calcula espesor desde mínimos de interferencia (Gordillo 2003)"""
        if self.selected_spectrum_idx is None:
            messagebox.showwarning("Advertencia", "Seleccione un espectro")
            return
        
        idx = self.selected_spectrum_idx
        spec = self.spectra_data[idx]
        
        # Detectar mínimos automáticamente
        T_inv = -spec['transmitance']
        peaks, _ = find_peaks(T_inv, distance=10, prominence=0.05)
        
        if len(peaks) < 2:
            messagebox.showwarning("Advertencia", "Se necesitan al menos 2 mínimos de interferencia.\nMarque manualmente con la herramienta 🔻")
            return
        
        s = float(self.substrate_n_var.get())
        minima = [(spec['wavelengths'][p], spec['transmitance'][p]) for p in peaks[:2]]
        
        # Calcular n en cada mínimo (Swanepoel Eq. 2)
        n_vals = []
        for lam, T_min in minima:
            M = (2*s/T_min) - (s**2 + 1)/2
            if M**2 >= s**2:
                n = np.sqrt(M + np.sqrt(M**2 - s**2))
                n_vals.append((lam, n))
        
        if len(n_vals) < 2:
            messagebox.showerror("Error", "No se pudieron calcular los índices de refracción")
            return
        
        # Eq. 3 de Gordillo: d = λ₁λ₂ / [2(n₁λ₂ - n₂λ₁)]
        (lam1, n1), (lam2, n2) = n_vals[0], n_vals[1]
        d_um = abs((lam1 * lam2) / (2 * (n1 * lam2 - n2 * lam1))) / 1000  # nm a μm
        
        self.thickness_var.set(f"{d_um:.3f}")
        spec['thickness_calculated'] = d_um
        
        self.log_message(f"Espesor calculado: {d_um:.3f} μm de {len(peaks)} mínimos detectados")
        messagebox.showinfo("Espesor calculado", 
                           f"d = {d_um:.3f} μm\n\n"
                           f"Basado en interferencia:\n"
                           f"• λ₁ = {lam1:.0f} nm, n₁ = {n1:.3f}\n"
                           f"• λ₂ = {lam2:.0f} nm, n₂ = {n2:.3f}")

    def calc_n_from_minima(self):
        """Calcula índice de refracción desde mínimos marcados manualmente"""
        if self.selected_spectrum_idx is None:
            return
        
        idx = self.selected_spectrum_idx
        minima = self.markers[idx].get('minima', [])
        
        if len(minima) < 2:
            messagebox.showwarning("Advertencia", "Marque al menos 2 mínimos")
            return
        
        minima.sort(key=lambda p: p[0])
        s = float(self.substrate_n_var.get())
        
        results = []
        for lam, T_min in minima:
            M = (2*s/T_min) - (s**2 + 1)/2
            if M**2 >= s**2:
                n = np.sqrt(M + np.sqrt(M**2 - s**2))
                results.append((lam, n))
                self.log_message(f"  λ = {lam:.0f} nm → n = {n:.4f}")
        
        if len(results) >= 2:
            # Calcular espesor
            (lam1, n1), (lam2, n2) = results[0], results[1]
            d_um = abs((lam1 * lam2) / (2 * (n1 * lam2 - n2 * lam1))) / 1000
            self.thickness_var.set(f"{d_um:.3f}")
            self.spectra_data[idx]['thickness_calculated'] = d_um
            self.log_message(f"Espesor desde mínimos manuales: {d_um:.3f} μm")

    def run_full_analysis(self):
        """Ejecuta análisis completo"""
        if self.selected_spectrum_idx is None:
            messagebox.showwarning("Advertencia", "Seleccione un espectro")
            return
        
        idx = self.selected_spectrum_idx
        spec = self.spectra_data[idx]
        
        try:
            d_um = float(self.thickness_var.get())
            d_cm = d_um * 1e-4
        except ValueError:
            messagebox.showerror("Error", "Espesor inválido")
            return
        
        # Calcular energía
        spec['E'] = 1239.84 / spec['wavelengths']
        
        # Calcular R si no existe
        if not spec.get('R'):
            n = len(spec['transmitance'])
            T_zone = spec['transmitance'][int(0.8*n):]
            T_avg = np.mean(T_zone)
            spec['R'] = (1 - T_avg) / (1 + T_avg)
            self.r_var.set(f"{spec['R']:.4f}")
            self.log_message(f"R calculado automáticamente: {spec['R']:.4f}")
        
        # Calcular α
        spec['alpha'] = self.calculate_alpha_bulk_essick(
            spec['transmitance'], spec['R'], d_cm
        )
        
        self.update_analysis_results()
        self.log_message("Análisis completo ejecutado")
        self.update_instructions(
            "✅ Análisis completo finalizado.\n\n"
            "AHORA PUEDE:\n"
            "• Ver gráficas Tauc con los botones de la derecha\n"
            "• Usar 'Play' para animación del ajuste\n"
            "• Ver valores moviendo el mouse sobre la gráfica"
        )

    def plot_tauc(self, gap_type):
        """Genera gráfica Tauc con información completa"""
        if self.selected_spectrum_idx is None:
            messagebox.showwarning("Advertencia", "Seleccione un espectro")
            return
        
        idx = self.selected_spectrum_idx
        spec = self.spectra_data[idx]
        
        if 'alpha' not in spec or 'E' not in spec:
            messagebox.showwarning("Advertencia", "Ejecute primero el análisis completo")
            return
        
        alpha = spec['alpha']
        E = spec['E']
        marks = self.markers.get(idx, {})
        
        fig, ax = plt.subplots(figsize=(12, 8), dpi=100)
        
        if gap_type == 'direct':
            y = (alpha * E)**2
            y_label = r'$(\alpha h\nu)^2$ [(eV·cm$^{-1}$)$^2$]'
            title = f'Tauc Plot - Gap Directo\n{spec["basename"]}'
        elif gap_type == 'indirect':
            y = np.sqrt(alpha)
            y_label = r'$\sqrt{\alpha}$ [(cm$^{-1}$)$^{1/2}$]'
            title = f'Tauc Plot - Gap Indirecto\n{spec["basename"]}'
        else:
            mask = alpha > 0
            y = np.log(alpha[mask])
            E = E[mask]
            y_label = r'$\ln(\alpha)$ [cm$^{-1}$]'
            title = f'Plot de Urbach\n{spec["basename"]}'
        
        # Datos experimentales
        ax.scatter(E, y, c='lightgray', alpha=0.6, s=30, label='Datos experimentales', zorder=1)
        
        # Buscar región de ajuste
        E_fit, y_fit = self.get_fit_region(E, y, spec, gap_type)
        
        if E_fit is not None and len(E_fit) > 5:
            self.plot_linear_fit(ax, E_fit, y_fit, gap_type)
        
        # Marcadores de referencia
        if marks.get('inflection'):
            E_inf = 1239.84 / marks['inflection'][0]
            ax.axvline(E_inf, color='red', linestyle=':', alpha=0.7, linewidth=2,
                      label=f'Inflexión: {E_inf:.3f} eV')
        
        if marks.get('edge_center'):
            E_cen = 1239.84 / marks['edge_center'][0]
            ax.axvline(E_cen, color='gold', linestyle='-', alpha=0.8, linewidth=2.5,
                      label=f'Centro canto: {E_cen:.3f} eV')
        
        # Regiones marcadas
        if marks.get('region1') and gap_type == 'indirect':
            x1, x2 = marks['region1']
            E1, E2 = 1239.84/x2, 1239.84/x1
            ax.axvspan(E1, E2, alpha=0.2, color='blue', label='Región 1 (pre-gap)')
        
        if marks.get('region2'):
            x1, x2 = marks['region2']
            E1, E2 = 1239.84/x2, 1239.84/x1
            ax.axvspan(E1, E2, alpha=0.2, color='green', label='Región 2 (post-gap)')
        
        ax.set_xlabel(r'$h\nu$ [eV]', fontsize=13)
        ax.set_ylabel(y_label, fontsize=13)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        # Panel de información
        info = f"Parámetros:\nd = {self.thickness_var.get()} μm\n"
        if spec.get('R'):
            info += f"R = {spec['R']:.4f}\n"
        info += f"α_max = {spec['alpha'].max():.1f} cm⁻¹"
        
        ax.text(0.02, 0.98, info, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', 
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout()
        plt.show()
        
        self.log_message(f"Gráfica Tauc ({gap_type}) generada")

    def get_fit_region(self, E, y, spec, gap_type):
        """Obtiene región de ajuste desde marcadores o auto-detección"""
        marks = self.markers.get(self.selected_spectrum_idx, {})
        
        if gap_type == 'indirect' and marks.get('region1') and marks.get('region2'):
            # Usar región 2 por defecto para ajuste (más estable)
            x1, x2 = marks['region2']
            mask = (spec['E'] >= 1239.84/x2) & (spec['E'] <= 1239.84/x1)
            return spec['E'][mask], y[mask]
        elif marks.get('region2'):
            x1, x2 = marks['region2']
            mask = (spec['E'] >= 1239.84/x2) & (spec['E'] <= 1239.84/x1)
            return spec['E'][mask], y[mask]
        
        # Auto-detección
        return E, y

    def plot_linear_fit(self, ax, E_fit, y_fit, gap_type):
        """Realiza y dibuja ajuste lineal"""
        try:
            coeffs = np.polyfit(E_fit, y_fit, 1)
            p = np.poly1d(coeffs)
            
            # Calcular R²
            y_pred = p(E_fit)
            ss_res = np.sum((y_fit - y_pred)**2)
            ss_tot = np.sum((y_fit - np.mean(y_fit))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Línea de ajuste
            E_line = np.linspace(E_fit.min(), E_fit.max(), 100)
            ax.plot(E_line, p(E_line), 'r--', linewidth=2.5, 
                   label=f'Ajuste: R² = {r_squared:.4f}')
            
            # Puntos usados
            ax.scatter(E_fit, y_fit, c='blue', s=40, alpha=0.7, 
                      label=f'Región ajuste ({len(E_fit)} pts)', zorder=3)
            
            # Calcular Eg
            if gap_type == 'direct':
                Eg = -coeffs[1]/coeffs[0] if coeffs[0] != 0 else 0
                ax.axvline(Eg, color='green', linestyle='-', linewidth=2.5, 
                          label=f'$E_g$ = {Eg:.3f} eV')
                ax.axhline(0, color='gray', linestyle=':', alpha=0.5)
            elif gap_type == 'indirect':
                Eg = -coeffs[1]/coeffs[0] if coeffs[0] != 0 else 0
                ax.axvline(Eg, color='green', linestyle='-', linewidth=2.5, 
                          label=f'$E_g$ ± $E_p$ = {Eg:.3f} eV')
            else:
                E0 = 1/coeffs[0] if coeffs[0] != 0 else float('inf')
                ax.text(0.05, 0.95, f'$E_0$ = {E0:.3f} eV', transform=ax.transAxes,
                       fontsize=12, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='wheat'))
                
        except Exception as e:
            self.log_message(f"Error en ajuste: {e}")

    def animate_tauc_fit(self, gap_type):
        """Animación del proceso de ajuste"""
        if self.selected_spectrum_idx is None:
            messagebox.showwarning("Advertencia", "Seleccione un espectro")
            return
        
        idx = self.selected_spectrum_idx
        spec = self.spectra_data[idx]
        
        if 'alpha' not in spec:
            messagebox.showwarning("Advertencia", "Ejecute primero el análisis")
            return
        
        self.stop_animation()
        self.animation_running = True
        
        alpha = spec['alpha']
        E = spec['E']
        
        if gap_type == 'direct':
            y = (alpha * E)**2
            y_label = r'$(\alpha h\nu)^2$'
        elif gap_type == 'indirect':
            y = np.sqrt(alpha)
            y_label = r'$\sqrt{\alpha}$'
        else:
            mask = alpha > 0
            y = np.log(alpha[mask])
            E = E[mask]
            y_label = r'$\ln(\alpha)$'
        
        self.anim_fig, self.anim_ax = plt.subplots(figsize=(10, 7))
        self.anim_ax.set_xlabel(r'$h\nu$ [eV]', fontsize=12)
        self.anim_ax.set_ylabel(y_label, fontsize=12)
        self.anim_ax.grid(True, alpha=0.3)
        
        self.anim_ax.scatter(E, y, c='lightgray', alpha=0.5, s=20)
        
        self.fit_line, = self.anim_ax.plot([], [], 'r-', linewidth=2)
        self.region_points = self.anim_ax.scatter([], [], c='blue', s=30)
        self.eg_line = self.anim_ax.axvline(x=0, color='green', linestyle='--', alpha=0)
        
        self.anim_text = self.anim_ax.text(0.02, 0.98, '', transform=self.anim_ax.transAxes,
                                          fontsize=10, verticalalignment='top',
                                          bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        n_frames = 40
        E_min, E_max = E.min(), E.max()
        E_range = E_max - E_min
        
        def init():
            self.fit_line.set_data([], [])
            self.eg_line.set_alpha(0)
            self.anim_text.set_text('Iniciando...')
            return self.fit_line, self.region_points, self.eg_line, self.anim_text
        
        def update(frame):
            if not self.animation_running:
                return self.fit_line, self.region_points, self.eg_line, self.anim_text
            
            window = E_range * 0.3
            start = E_min + (frame / n_frames) * (E_range - window)
            end = start + window
            
            mask = (E >= start) & (E <= end)
            if np.sum(mask) < 5:
                return self.fit_line, self.region_points, self.eg_line, self.anim_text
            
            E_w, y_w = E[mask], y[mask]
            
            try:
                c = np.polyfit(E_w, y_w, 1)
                p = np.poly1d(c)
                
                y_p = p(E_w)
                r2 = 1 - np.sum((y_w - y_p)**2) / np.sum((y_w - np.mean(y_w))**2)
                
                E_line = np.linspace(E_w.min(), E_w.max(), 100)
                self.fit_line.set_data(E_line, p(E_line))
                self.region_points.set_offsets(np.c_[E_w, y_w])
                
                if gap_type in ['direct', 'indirect']:
                    Eg = -c[1]/c[0] if c[0] != 0 else 0
                    self.eg_line.set_xdata([Eg, Eg])
                    self.eg_line.set_alpha(0.7)
                    self.anim_ax.set_title(f'Frame {frame+1}/{n_frames} - Eg={Eg:.3f}eV, R²={r2:.3f}')
                else:
                    self.anim_ax.set_title(f'Frame {frame+1}/{n_frames} - R²={r2:.3f}')
                
                info = f"Rango: {start:.3f}-{end:.3f} eV\nR²: {r2:.4f}\nPuntos: {len(E_w)}"
                self.anim_text.set_text(info)
                
            except:
                pass
            
            return self.fit_line, self.region_points, self.eg_line, self.anim_text
        
        self.current_animation = FuncAnimation(self.anim_fig, update, frames=n_frames,
                                              init_func=init, interval=200, repeat=True)
        plt.tight_layout()
        plt.show()

    def stop_animation(self):
        """Detiene animación"""
        self.animation_running = False
        if self.current_animation:
            self.current_animation.event_source.stop()
        if hasattr(self, 'anim_fig'):
            plt.close(self.anim_fig)

    # ========== MÉTODOS AUXILIARES ==========

    def update_point_values(self, x):
        """Actualiza panel de valores en punto"""
        if self.selected_spectrum_idx is None:
            return
        
        idx = self.selected_spectrum_idx
        spec = self.spectra_data[idx]
        
        i_near = np.argmin(np.abs(spec['wavelengths'] - x))
        lam = spec['wavelengths'][i_near]
        T = spec['transmitance'][i_near]
        E = 1239.84 / lam
        
        text = f"📍 λ = {lam:.2f} nm\n⚡ E = {E:.4f} eV\n📊 T = {T:.4f}"
        
        if spec.get('R'):
            text += f"\n🔴 R = {spec['R']:.4f}"
            try:
                d_cm = float(self.thickness_var.get()) * 1e-4
                alpha = self.calculate_alpha_bulk_essick(np.array([T]), spec['R'], d_cm)[0]
                text += f"\n⚫ α = {alpha:.2f} cm⁻¹"
                text += f"\n📐 (αE)² = {(alpha*E)**2:.2e}"
                text += f"\n📐 √α = {np.sqrt(alpha):.2f}"
            except:
                pass
        
        self.point_values_text.delete(1.0, tk.END)
        self.point_values_text.insert(1.0, text)

    def add_to_audit(self, step, variable, formula, values, result, status, parent=""):
        item = self.audit_tree.insert(parent, 'end', text=step, 
                                     values=(variable, formula, values, result, status))
        if "✗" in status or "ERROR" in status:
            self.audit_tree.item(item, tags=('error',))
        elif "WARN" in status:
            self.audit_tree.item(item, tags=('warning',))
        elif "✓" in status or "OK" in status:
            self.audit_tree.item(item, tags=('ok',))
        self.audit_tree.tag_configure('error', foreground='red')
        self.audit_tree.tag_configure('warning', foreground='orange')
        self.audit_tree.tag_configure('ok', foreground='green')
        if parent:
            self.audit_tree.item(parent, open=True)
        return item

    def refresh_audit(self):
        pass

    def clear_audit(self):
        for item in self.audit_tree.get_children():
            self.audit_tree.delete(item)

    def save_audit_report(self):
        pass

    def update_analysis_results(self):
        if self.selected_spectrum_idx is None:
            return
        idx = self.selected_spectrum_idx
        spec = self.spectra_data[idx]
        text = f"RESULTADOS: {spec['basename']}\n" + "="*50 + "\n"
        if 'alpha' in spec:
            text += f"Rango α: {spec['alpha'].min():.1f} - {spec['alpha'].max():.1f} cm⁻¹\n"
            text += f"Rango E: {spec['E'].min():.3f} - {spec['E'].max():.3f} eV\n"
        if spec.get('R'):
            text += f"R: {spec['R']:.4f}\n"
        self.quick_results_text.delete(1.0, tk.END)
        self.quick_results_text.insert(1.0, text)

    # ========== MÉTODOS DE ARCHIVO Y GRÁFICA ==========

    def parse_sp_file(self, filename):
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            wavelengths, transmitance = [], []
            start_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('#DATA'):
                    start_idx = i + 1
                    break
            for line in lines[start_idx:]:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        wavelengths.append(float(parts[0]))
                        transmitance.append(float(parts[1]) / 100.0)
                    except ValueError:
                        continue
            return np.array(wavelengths), np.array(transmitance)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo: {str(e)}")
            return None, None

    def load_files(self):
        filenames = filedialog.askopenfilenames(filetypes=[("SP files", "*.sp"), ("All files", "*.*")])
        if not filenames:
            return
        for fname in filenames:
            if any(d['filename'] == fname for d in self.spectra_data):
                continue
            wl, T = self.parse_sp_file(fname)
            if wl is not None and len(wl) > 0:
                color = self.colors[len(self.spectra_data) % len(self.colors)]
                self.spectra_data.append({
                    'filename': fname, 'basename': os.path.basename(fname),
                    'wavelengths': wl, 'transmitance': T, 'color': color,
                    'visible': True, 'line': None, 'alpha': None, 'E': None, 'R': None,
                })
                self.files_listbox.insert(tk.END, os.path.basename(fname))
                self.markers[len(self.spectra_data)-1] = {
                    'inflection': None, 'region1': None, 'region2': None,
                    'edge_center': None, 'minima': []
                }
                self.log_message(f"Cargado: {os.path.basename(fname)}")
        if self.spectra_data:
            self.plot_data()

    def clear_all(self):
        self.spectra_data = []
        self.files_listbox.delete(0, tk.END)
        self.markers.clear()
        self.ax.clear()
        self.canvas.draw()

    def plot_data(self):
        self.ax.clear()
        for i, spec in enumerate(self.spectra_data):
            if spec['visible']:
                line, = self.ax.plot(spec['wavelengths'], spec['transmitance'],
                                   color=spec['color'], linewidth=2, label=spec['basename'])
                spec['line'] = line
        self.ax.set_xlabel(self.xlabel_var.get())
        self.ax.set_ylabel(self.ylabel_var.get())
        self.ax.set_title(self.title_var.get())
        if self.grid_var.get():
            self.ax.grid(True, alpha=0.3)
        if len([s for s in self.spectra_data if s['visible']]) > 0:
            self.ax.legend(loc='best', fontsize=8)
        self.apply_axes_range()

    def update_plot(self):
        if self.spectra_data:
            self.plot_data()

    def on_select_file(self, event):
        selection = self.files_listbox.curselection()
        if selection:
            self.selected_spectrum_idx = selection[0]

    def toggle_selected(self):
        selected = self.files_listbox.curselection()
        for idx in selected:
            self.spectra_data[idx]['visible'] = not self.spectra_data[idx]['visible']
        self.plot_data()

    def change_color(self):
        selected = self.files_listbox.curselection()
        if not selected:
            return
        color = colorchooser.askcolor(title="Seleccionar color")[1]
        if color:
            for idx in selected:
                self.spectra_data[idx]['color'] = color
            self.plot_data()

    def remove_selected(self):
        selected = self.files_listbox.curselection()
        if not selected:
            return
        for idx in sorted(selected, reverse=True):
            del self.spectra_data[idx]
            self.files_listbox.delete(idx)

    def auto_axes(self):
        if not self.spectra_data:
            return
        visible = [s for s in self.spectra_data if s['visible']]
        if not visible:
            return
        self.xmin_var.set(f"{min(s['wavelengths'].min() for s in visible):.1f}")
        self.xmax_var.set(f"{max(s['wavelengths'].max() for s in visible):.1f}")
        self.ymin_var.set(f"{min(s['transmitance'].min() for s in visible):.3f}")
        self.ymax_var.set(f"{max(s['transmitance'].max() for s in visible):.3f}")
        self.apply_axes_range()

    def apply_axes_range(self):
        try:
            xmin = float(self.xmin_var.get()) if self.xmin_var.get() else None
            xmax = float(self.xmax_var.get()) if self.xmax_var.get() else None
            ymin = float(self.ymin_var.get()) if self.ymin_var.get() else None
            ymax = float(self.ymax_var.get()) if self.ymax_var.get() else None
            if xmin is not None and xmax is not None:
                self.ax.set_xlim(xmin, xmax)
            if ymin is not None and ymax is not None:
                self.ax.set_ylim(ymin, ymax)
            self.canvas.draw()
        except ValueError:
            pass

    def reset_axes(self):
        self.xmin_var.set("")
        self.xmax_var.set("")
        self.ymin_var.set("")
        self.ymax_var.set("")
        self.auto_axes()

    def calc_R_from_transparent(self):
        if self.selected_spectrum_idx is None:
            return
        spec = self.spectra_data[self.selected_spectrum_idx]
        n = len(spec['transmitance'])
        T_zone = spec['transmitance'][int(0.8*n):]
        T_avg = np.mean(T_zone)
        R = (1 - T_avg) / (1 + T_avg)
        self.r_var.set(f"{R:.4f}")
        spec['R'] = R
        self.log_message(f"R calculado: {R:.4f}")

    def clear_markers_current(self):
        if self.selected_spectrum_idx is not None:
            idx = self.selected_spectrum_idx
            self.markers[idx] = {'inflection': None, 'region1': None, 'region2': None,
                               'edge_center': None, 'minima': []}
            self.redraw_markers()
            self.log_message("Marcadores borrados")

    def save_plot(self):
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if filename:
            self.fig.savefig(filename, dpi=300, bbox_inches='tight')

    def export_csv(self):
        pass

    def create_files_tab(self, parent):
        ttk.Button(parent, text="➕ Agregar archivos .sp", command=self.load_files).pack(fill=tk.X, pady=2)
        ttk.Button(parent, text="🗑️ Limpiar todo", command=self.clear_all).pack(fill=tk.X, pady=2)
        ttk.Label(parent, text="Archivos cargados:").pack(anchor=tk.W, pady=(5,2))
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.files_listbox = tk.Listbox(list_frame, height=12, selectmode=tk.EXTENDED, font=('Courier', 9))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=scrollbar.set)
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.files_listbox.bind('<<ListboxSelect>>', self.on_select_file)
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="👁️", command=self.toggle_selected).pack(side=tk.LEFT, padx=1, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="🎨", command=self.change_color).pack(side=tk.LEFT, padx=1, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="🗑️", command=self.remove_selected).pack(side=tk.LEFT, padx=1, fill=tk.X, expand=True)

    def create_plot_settings_tab(self, parent):
        ttk.Label(parent, text="Título:").pack(anchor=tk.W)
        self.title_var = tk.StringVar(value="Espectros de Transmitancia")
        ttk.Entry(parent, textvariable=self.title_var).pack(fill=tk.X, pady=1)
        ttk.Label(parent, text="Eje X:").pack(anchor=tk.W)
        self.xlabel_var = tk.StringVar(value="Longitud de onda (nm)")
        ttk.Entry(parent, textvariable=self.xlabel_var).pack(fill=tk.X, pady=1)
        ttk.Label(parent, text="Eje Y:").pack(anchor=tk.W)
        self.ylabel_var = tk.StringVar(value="Transmitancia")
        ttk.Entry(parent, textvariable=self.ylabel_var).pack(fill=tk.X, pady=1)
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Mostrar cuadrícula", variable=self.grid_var, command=self.update_plot).pack(anchor=tk.W)
        axes_frame = ttk.LabelFrame(parent, text="Rangos", padding="5")
        axes_frame.pack(fill=tk.X, pady=5)
        for i, (label, var_name) in enumerate([("X min:", 'xmin'), ("X max:", 'xmax'), ("Y min:", 'ymin'), ("Y max:", 'ymax')]):
            ttk.Label(axes_frame, text=label).grid(row=i//2, column=(i%2)*2, sticky=tk.W)
            setattr(self, f'{var_name}_var', tk.StringVar())
            ttk.Entry(axes_frame, textvariable=getattr(self, f'{var_name}_var'), width=8).grid(row=i//2, column=(i%2)*2+1, padx=2)
        btn_range = ttk.Frame(axes_frame)
        btn_range.grid(row=2, column=0, columnspan=4, pady=5)
        ttk.Button(btn_range, text="Auto", command=self.auto_axes).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_range, text="Aplicar", command=self.apply_axes_range).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_range, text="Reset", command=self.reset_axes).pack(side=tk.LEFT, padx=1)

    def create_analysis_tab(self, parent):
        mode_frame = ttk.LabelFrame(parent, text="Modo", padding="5")
        mode_frame.pack(fill=tk.X, pady=2)
        self.analysis_mode = tk.StringVar(value="manual")
        ttk.Radiobutton(mode_frame, text="Manual", variable=self.analysis_mode, value="manual").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Automático", variable=self.analysis_mode, value="auto").pack(anchor=tk.W)
        
        sample_frame = ttk.LabelFrame(parent, text="Tipo de muestra", padding="5")
        sample_frame.pack(fill=tk.X, pady=2)
        self.sample_type = tk.StringVar(value="bulk")
        ttk.Radiobutton(sample_frame, text="🔷 Bulk", variable=self.sample_type, value="bulk", command=self.on_sample_type_change).pack(anchor=tk.W)
        ttk.Radiobutton(sample_frame, text="🔶 Película", variable=self.sample_type, value="thin", command=self.on_sample_type_change).pack(anchor=tk.W)
        
        self.gap_frame = ttk.LabelFrame(parent, text="Tipo de gap", padding="5")
        self.gap_frame.pack(fill=tk.X, pady=2)
        self.gap_type = tk.StringVar(value="direct")
        ttk.Radiobutton(self.gap_frame, text="⚡ Directo", variable=self.gap_type, value="direct").pack(anchor=tk.W)
        ttk.Radiobutton(self.gap_frame, text="🌊 Indirecto", variable=self.gap_type, value="indirect").pack(anchor=tk.W)
        ttk.Radiobutton(self.gap_frame, text="📉 Urbach", variable=self.gap_type, value="urbach").pack(anchor=tk.W)
        
        params_frame = ttk.LabelFrame(parent, text="Parámetros", padding="5")
        params_frame.pack(fill=tk.X, pady=2)
        ttk.Label(params_frame, text="d (μm):").grid(row=0, column=0, sticky=tk.W)
        self.thickness_var = tk.StringVar(value="1.0")
        ttk.Entry(params_frame, textvariable=self.thickness_var, width=10).grid(row=0, column=1, padx=2)
        ttk.Button(params_frame, text="Auto", command=self.calc_thickness_from_interference).grid(row=0, column=2, padx=2)
        ttk.Label(params_frame, text="s:").grid(row=1, column=0, sticky=tk.W)
        self.substrate_n_var = tk.StringVar(value="1.5")
        self.substrate_entry = ttk.Entry(params_frame, textvariable=self.substrate_n_var, width=10)
        self.substrate_entry.grid(row=1, column=1, padx=2)
        ttk.Label(params_frame, text="R:").grid(row=2, column=0, sticky=tk.W)
        self.r_var = tk.StringVar()
        ttk.Entry(params_frame, textvariable=self.r_var, width=10).grid(row=2, column=1, padx=2)
        ttk.Button(params_frame, text="Calc", command=self.calc_R_from_transparent).grid(row=2, column=2, padx=2)
        
        ttk.Button(parent, text="🚀 Ejecutar Análisis", command=self.run_full_analysis, style='Accent.TButton').pack(fill=tk.X, pady=5)

    def on_sample_type_change(self):
        if self.sample_type.get() == "bulk":
            self.substrate_entry.config(state='disabled')
            self.gap_frame.pack()
        else:
            self.substrate_entry.config(state='normal')
            self.gap_frame.pack_forget()

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

def main():
    root = tk.Tk()
    app = SpectrometerViewer(root)
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Archivo", menu=file_menu)
    file_menu.add_command(label="Cargar", command=app.load_files)
    file_menu.add_command(label="Guardar", command=app.save_plot)
    file_menu.add_separator()
    file_menu.add_command(label="Salir", command=root.quit)
    root.mainloop()

if __name__ == "__main__":
    main()
