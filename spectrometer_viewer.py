import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import os

class SpectrometerViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Perkin Elmer Lambda 35 - Visor de Múltiples Espectros")
        self.root.geometry("1400x800")
        
        # Variables
        self.spectra_data = []  # Lista para almacenar múltiples espectros
        self.colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'gray', 'olive', 'cyan']
        
        # Configurar el estilo
        self.root.configure(bg='#f0f0f0')
        
        # Crear la interfaz
        self.create_widgets()
        
    def create_widgets(self):
        # Frame principal con paneles
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Panel de control izquierdo
        control_frame = ttk.Frame(main_paned, padding="10")
        main_paned.add(control_frame, weight=1)
        
        # Panel derecho para la gráfica
        plot_frame = ttk.Frame(main_paned, padding="10")
        main_paned.add(plot_frame, weight=4)
        
        # ========== PANEL DE CONTROL ==========
        
        # Frame para carga de archivos
        file_frame = ttk.LabelFrame(control_frame, text="Cargar Archivos", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_frame, text="Agregar Archivo(s) .sp", 
                  command=self.load_files).pack(fill=tk.X, pady=5)
        
        ttk.Button(file_frame, text="Limpiar Todo", 
                  command=self.clear_all).pack(fill=tk.X, pady=5)
        
        # Lista de archivos cargados
        ttk.Label(file_frame, text="Archivos cargados:").pack(anchor=tk.W, pady=(10,5))
        
        # Frame para la lista con scrollbar
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.files_listbox = tk.Listbox(list_frame, height=8, selectmode=tk.EXTENDED)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind eventos de la lista
        self.files_listbox.bind('<<ListboxSelect>>', self.on_select_file)
        
        # Botones para manipular archivos seleccionados
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Ocultar/Mostrar", 
                  command=self.toggle_selected).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(btn_frame, text="Cambiar Color", 
                  command=self.change_color).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(btn_frame, text="Eliminar", 
                  command=self.remove_selected).pack(side=tk.LEFT, padx=2)
        
        # ========== AJUSTES DE GRÁFICA ==========
        
        # Frame para ajustes generales
        general_frame = ttk.LabelFrame(control_frame, text="Ajustes Generales", padding="10")
        general_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(general_frame, text="Título:").pack(anchor=tk.W)
        self.title_var = tk.StringVar(value="Espectros de Absorbancia")
        ttk.Entry(general_frame, textvariable=self.title_var).pack(fill=tk.X, pady=2)
        
        ttk.Label(general_frame, text="Etiqueta X:").pack(anchor=tk.W)
        self.xlabel_var = tk.StringVar(value="Longitud de onda (nm)")
        ttk.Entry(general_frame, textvariable=self.xlabel_var).pack(fill=tk.X, pady=2)
        
        ttk.Label(general_frame, text="Etiqueta Y:").pack(anchor=tk.W)
        self.ylabel_var = tk.StringVar(value="Absorbancia")
        ttk.Entry(general_frame, textvariable=self.ylabel_var).pack(fill=tk.X, pady=2)
        
        # Checkbox para cuadrícula
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(general_frame, text="Mostrar cuadrícula", 
                       variable=self.grid_var, command=self.update_plot).pack(anchor=tk.W, pady=2)
        
        # ========== RANGOS DE EJES ==========
        
        axes_frame = ttk.LabelFrame(control_frame, text="Rangos de Ejes", padding="10")
        axes_frame.pack(fill=tk.X, pady=5)
        
        # Rango X
        ttk.Label(axes_frame, text="Eje X (nm):", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        x_range_frame = ttk.Frame(axes_frame)
        x_range_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(x_range_frame, text="Min:").pack(side=tk.LEFT)
        self.xmin_var = tk.StringVar()
        self.xmin_entry = ttk.Entry(x_range_frame, textvariable=self.xmin_var, width=10)
        self.xmin_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(x_range_frame, text="Max:").pack(side=tk.LEFT, padx=(10,0))
        self.xmax_var = tk.StringVar()
        self.xmax_entry = ttk.Entry(x_range_frame, textvariable=self.xmax_var, width=10)
        self.xmax_entry.pack(side=tk.LEFT, padx=5)
        
        # Rango Y
        ttk.Label(axes_frame, text="Eje Y (Absorbancia):", font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(10,0))
        
        y_range_frame = ttk.Frame(axes_frame)
        y_range_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(y_range_frame, text="Min:").pack(side=tk.LEFT)
        self.ymin_var = tk.StringVar()
        self.ymin_entry = ttk.Entry(y_range_frame, textvariable=self.ymin_var, width=10)
        self.ymin_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(y_range_frame, text="Max:").pack(side=tk.LEFT, padx=(10,0))
        self.ymax_var = tk.StringVar()
        self.ymax_entry = ttk.Entry(y_range_frame, textvariable=self.ymax_var, width=10)
        self.ymax_entry.pack(side=tk.LEFT, padx=5)
        
        # Botones para rangos
        range_buttons = ttk.Frame(axes_frame)
        range_buttons.pack(fill=tk.X, pady=10)
        
        ttk.Button(range_buttons, text="Auto-ajustar", 
                  command=self.auto_axes).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(range_buttons, text="Aplicar Rango", 
                  command=self.apply_axes_range).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(range_buttons, text="Resetear", 
                  command=self.reset_axes).pack(side=tk.LEFT, padx=2)
        
        # Botón para actualizar todo
        ttk.Button(control_frame, text="Actualizar Gráfica", 
                  command=self.update_plot, style='Accent.TButton').pack(fill=tk.X, pady=10)
        
        # ========== PANEL DE GRÁFICA ==========
        
        # Crear figura de matplotlib
        self.fig = Figure(figsize=(10, 7), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # Canvas para la figura
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Barra de herramientas de matplotlib
        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.pack(fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
        # Frame para estadísticas
        stats_frame = ttk.LabelFrame(plot_frame, text="Estadísticas", padding="5")
        stats_frame.pack(fill=tk.X, pady=(10,0))
        
        self.stats_text = tk.Text(stats_frame, height=4, font=('Courier', 9))
        self.stats_text.pack(fill=tk.X)
        
    def parse_sp_file(self, filename):
        """Parsea el archivo .sp del espectrofotómetro"""
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            wavelengths = []
            absorbance = []
            
            # Buscar donde comienzan los datos
            start_idx = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#') and not line.startswith('$'):
                    try:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            float(parts[0])
                            float(parts[1])
                            start_idx = i
                            break
                    except ValueError:
                        continue
            
            # Leer los datos
            for line in lines[start_idx:]:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('$'):
                    try:
                        parts = line.split()
                        if len(parts) >= 2:
                            wl = float(parts[0])
                            abs_val = float(parts[1])
                            wavelengths.append(wl)
                            absorbance.append(abs_val)
                    except ValueError:
                        continue
            
            return np.array(wavelengths), np.array(absorbance)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al leer el archivo: {str(e)}")
            return None, None
    
    def load_files(self):
        """Cargar múltiples archivos .sp"""
        filenames = filedialog.askopenfilenames(
            title="Seleccionar archivos .sp",
            filetypes=[("SP files", "*.sp"), ("All files", "*.*")]
        )
        
        if not filenames:
            return
        
        for filename in filenames:
            # Verificar si el archivo ya está cargado
            if any(d['filename'] == filename for d in self.spectra_data):
                continue
                
            wavelengths, absorbance = self.parse_sp_file(filename)
            
            if wavelengths is not None and len(wavelengths) > 0:
                # Asignar color automático
                color_idx = len(self.spectra_data) % len(self.colors)
                
                # Crear entrada para el espectro
                spectrum = {
                    'filename': filename,
                    'basename': os.path.basename(filename),
                    'wavelengths': wavelengths,
                    'absorbance': absorbance,
                    'color': self.colors[color_idx],
                    'visible': True,
                    'line': None
                }
                
                self.spectra_data.append(spectrum)
                self.files_listbox.insert(tk.END, os.path.basename(filename))
        
        if self.spectra_data:
            self.plot_data()
            self.update_stats()
            messagebox.showinfo("Éxito", f"Se cargaron {len(filenames)} archivos")
    
    def plot_data(self):
        """Graficar todos los datos"""
        self.ax.clear()
        
        # Graficar cada espectro visible
        for spectrum in self.spectra_data:
            if spectrum['visible']:
                line, = self.ax.plot(spectrum['wavelengths'], spectrum['absorbance'], 
                                    color=spectrum['color'], 
                                    linewidth=2,
                                    label=spectrum['basename'])
                spectrum['line'] = line
        
        # Configurar etiquetas y título
        self.ax.set_xlabel(self.xlabel_var.get(), fontsize=12)
        self.ax.set_ylabel(self.ylabel_var.get(), fontsize=12)
        self.ax.set_title(self.title_var.get(), fontsize=14)
        
        # Cuadrícula
        if self.grid_var.get():
            self.ax.grid(True, alpha=0.3)
        
        # Leyenda
        if len([s for s in self.spectra_data if s['visible']]) > 0:
            self.ax.legend(loc='best', fontsize=9)
        
        # Aplicar rangos si están definidos
        self.apply_axes_range()
        
        self.canvas.draw()
    
    def update_plot(self):
        """Actualizar la gráfica con los ajustes actuales"""
        if self.spectra_data:
            self.plot_data()
    
    def on_select_file(self, event):
        """Evento al seleccionar archivos en la lista"""
        pass
    
    def toggle_selected(self):
        """Ocultar/mostrar archivos seleccionados"""
        selected = self.files_listbox.curselection()
        for idx in selected:
            self.spectra_data[idx]['visible'] = not self.spectra_data[idx]['visible']
        self.plot_data()
    
    def change_color(self):
        """Cambiar color de los archivos seleccionados"""
        selected = self.files_listbox.curselection()
        if not selected:
            messagebox.showwarning("Advertencia", "Selecciona al menos un archivo")
            return
        
        color = colorchooser.askcolor(title="Seleccionar color")[1]
        if color:
            for idx in selected:
                self.spectra_data[idx]['color'] = color
            self.plot_data()
    
    def remove_selected(self):
        """Eliminar archivos seleccionados"""
        selected = self.files_listbox.curselection()
        if not selected:
            messagebox.showwarning("Advertencia", "Selecciona al menos un archivo")
            return
        
        # Eliminar en orden inverso para no afectar índices
        for idx in sorted(selected, reverse=True):
            del self.spectra_data[idx]
            self.files_listbox.delete(idx)
        
        if self.spectra_data:
            self.plot_data()
            self.update_stats()
        else:
            self.ax.clear()
            self.ax.set_xlabel(self.xlabel_var.get())
            self.ax.set_ylabel(self.ylabel_var.get())
            self.ax.set_title(self.title_var.get())
            self.canvas.draw()
            self.stats_text.delete(1.0, tk.END)
    
    def clear_all(self):
        """Limpiar todos los archivos"""
        self.spectra_data = []
        self.files_listbox.delete(0, tk.END)
        self.ax.clear()
        self.ax.set_xlabel(self.xlabel_var.get())
        self.ax.set_ylabel(self.ylabel_var.get())
        self.ax.set_title(self.title_var.get())
        self.canvas.draw()
        self.stats_text.delete(1.0, tk.END)
    
    def update_stats(self):
        """Actualizar estadísticas de los espectros"""
        self.stats_text.delete(1.0, tk.END)
        
        if not self.spectra_data:
            return
        
        stats = "Estadísticas de espectros visibles:\n"
        
        for i, spectrum in enumerate(self.spectra_data):
            if spectrum['visible']:
                stats += f"{spectrum['basename'][:20]:20s}: "
                stats += f"λ: {spectrum['wavelengths'].min():.1f}-{spectrum['wavelengths'].max():.1f} nm, "
                stats += f"Abs: {spectrum['absorbance'].min():.3f}-{spectrum['absorbance'].max():.3f}\n"
        
        self.stats_text.insert(1.0, stats)
    
    def auto_axes(self):
        """Auto-ajustar los ejes basado en datos visibles"""
        if not self.spectra_data:
            return
        
        # Encontrar rangos de todos los espectros visibles
        x_min, x_max = float('inf'), float('-inf')
        y_min, y_max = float('inf'), float('-inf')
        
        for spectrum in self.spectra_data:
            if spectrum['visible']:
                x_min = min(x_min, spectrum['wavelengths'].min())
                x_max = max(x_max, spectrum['wavelengths'].max())
                y_min = min(y_min, spectrum['absorbance'].min())
                y_max = max(y_max, spectrum['absorbance'].max())
        
        # Agregar un pequeño margen
        x_range = x_max - x_min
        y_range = y_max - y_min
        
        x_min = x_min - 0.02 * x_range
        x_max = x_max + 0.02 * x_range
        y_min = y_min - 0.05 * y_range
        y_max = y_max + 0.05 * y_range
        
        # Actualizar variables
        self.xmin_var.set(f"{x_min:.1f}")
        self.xmax_var.set(f"{x_max:.1f}")
        self.ymin_var.set(f"{y_min:.3f}")
        self.ymax_var.set(f"{y_max:.3f}")
        
        # Aplicar rango
        self.apply_axes_range()
    
    def apply_axes_range(self):
        """Aplicar el rango de ejes especificado"""
        try:
            x_min = float(self.xmin_var.get()) if self.xmin_var.get() else None
            x_max = float(self.xmax_var.get()) if self.xmax_var.get() else None
            y_min = float(self.ymin_var.get()) if self.ymin_var.get() else None
            y_max = float(self.ymax_var.get()) if self.ymax_var.get() else None
            
            if x_min is not None and x_max is not None:
                self.ax.set_xlim(x_min, x_max)
            if y_min is not None and y_max is not None:
                self.ax.set_ylim(y_min, y_max)
                
            self.canvas.draw()
        except ValueError:
            pass
    
    def reset_axes(self):
        """Resetear los ejes a valores por defecto"""
        self.xmin_var.set("")
        self.xmax_var.set("")
        self.ymin_var.set("")
        self.ymax_var.set("")
        self.auto_axes()
    
    def save_plot(self):
        """Guardar la gráfica como imagen"""
        if not self.spectra_data:
            messagebox.showwarning("Advertencia", "No hay datos para guardar")
            return
        
        filetypes = [
            ('PNG', '*.png'),
            ('PDF', '*.pdf'),
            ('SVG', '*.svg'),
            ('JPG', '*.jpg'),
            ('TIFF', '*.tiff')
        ]
        
        filename = filedialog.asksaveasfilename(
            title="Guardar gráfica como",
            defaultextension=".png",
            filetypes=filetypes
        )
        
        if filename:
            try:
                self.fig.savefig(filename, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Éxito", f"Gráfica guardada en:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {str(e)}")
    
    def export_csv(self):
        """Exportar datos a CSV"""
        if not self.spectra_data:
            messagebox.showwarning("Advertencia", "No hay datos para exportar")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Exportar datos como CSV",
            defaultextension=".csv",
            filetypes=[('CSV', '*.csv'), ('All files', '*.*')]
        )
        
        if filename:
            try:
                # Crear encabezado
                header = "Longitud_onda_nm"
                for spectrum in self.spectra_data:
                    if spectrum['visible']:
                        header += f",{spectrum['basename']}"
                
                # Encontrar la longitud máxima de los datos
                max_len = max(len(s['wavelengths']) for s in self.spectra_data if s['visible'])
                
                # Crear matriz de datos
                data = []
                for i in range(max_len):
                    row = []
                    first = True
                    for spectrum in self.spectra_data:
                        if spectrum['visible']:
                            if first:
                                if i < len(spectrum['wavelengths']):
                                    row.append(spectrum['wavelengths'][i])
                                else:
                                    row.append('')
                                first = False
                            if i < len(spectrum['absorbance']):
                                row.append(spectrum['absorbance'][i])
                            else:
                                row.append('')
                    data.append(row)
                
                # Guardar archivo
                np.savetxt(filename, data, delimiter=',', header=header, comments='', fmt='%s')
                messagebox.showinfo("Éxito", f"Datos exportados a:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar: {str(e)}")

def main():
    root = tk.Tk()
    
    # Configurar estilo para botón acentuado
    style = ttk.Style()
    style.configure('Accent.TButton', font=('Arial', 10, 'bold'))
    
    app = SpectrometerViewer(root)
    
    # Agregar menú
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Archivo", menu=file_menu)
    file_menu.add_command(label="Cargar archivos", command=app.load_files)
    file_menu.add_command(label="Guardar gráfica", command=app.save_plot)
    file_menu.add_command(label="Exportar CSV", command=app.export_csv)
    file_menu.add_separator()
    file_menu.add_command(label="Salir", command=root.quit)
    
    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Ver", menu=view_menu)
    view_menu.add_command(label="Auto-ajustar ejes", command=app.auto_axes)
    view_menu.add_command(label="Resetear vista", command=app.reset_axes)
    
    root.mainloop()

if __name__ == "__main__":
    main()
