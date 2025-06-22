import os
import cv2
import numpy as np
from skimage import measure
import svgwrite
from scipy.interpolate import splprep, splev
import cairosvg
import base64
from PIL import Image
import io
import glob
import re

class PatternService:
    def __init__(self):
        self.dpi = 96
        self.pixel_to_mm = 25.4 / self.dpi  # 0.26458 mm per pixel
        self.scale_factor = 20  # Escala para patrones funcionales
        
    def draw_ruler(self, dwg, max_length_mm, scale_factor, axis='x', interval=10, size=5):
        """Draw ruler ticks and labels along the X or Y axis, adjusted for scaling."""
        for i in range(0, int(max_length_mm / scale_factor) + 1, interval):
            if axis == 'x':
                x = i * scale_factor
                dwg.add(dwg.line(start=(x, 0), end=(x, size), stroke='gray', stroke_width=0.3))
                dwg.add(dwg.text(str(i), insert=(x + 1, size + 3), font_size="2px", fill='gray'))
            elif axis == 'y':
                y = i * scale_factor
                dwg.add(dwg.line(start=(0, y), end=(size, y), stroke='gray', stroke_width=0.3))
                dwg.add(dwg.text(str(i), insert=(size + 1, y + 1.5), font_size="2px", fill='gray'))

    def smooth_contour(self, contour, smooth_factor=0.1):
        """Suaviza un contorno usando splines."""
        contour = np.array(contour)
        if len(contour) < 3:
            return contour

        x, y = contour[:, 1], contour[:, 0]

        # Eliminar puntos duplicados
        mask = np.ones(len(x), dtype=bool)
        for i in range(1, len(x)):
            if np.allclose([x[i], y[i]], [x[i-1], y[i-1]], atol=1e-6):
                mask[i] = False
        x, y = x[mask], y[mask]

        # Cerrar el contorno
        x = np.append(x, x[0])
        y = np.append(y, y[0])

        if len(x) < 3:
            return contour

        try:
            tck, u = splprep([x, y], s=smooth_factor, per=True)
            u_fine = np.linspace(0, 1, len(contour) * 2)
            x_smooth, y_smooth = splev(u_fine, tck)
            return np.column_stack((y_smooth, x_smooth))
        except ValueError as e:
            print(f"Error smoothing contour: {e}. Returning original contour.")
            return contour

    def png_to_svg(self, image_path, output_path):
        """Convierte una imagen PNG a SVG con contornos suavizados."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"No se pudo cargar la imagen: {image_path}")
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            
            kernel = np.ones((3, 3), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            contours = measure.find_contours(binary, level=0.8)
            
            height, width = binary.shape
            width_mm = width * self.pixel_to_mm
            height_mm = height * self.pixel_to_mm
            
            scaled_width_mm = width_mm * self.scale_factor
            scaled_height_mm = height_mm * self.scale_factor
            
            dwg = svgwrite.Drawing(output_path, 
                                 size=(f"{scaled_width_mm}mm", f"{scaled_height_mm}mm"),
                                 viewBox=f"0 0 {scaled_width_mm} {scaled_height_mm}")
            
            # Agregar reglas
            dwg.add(dwg.line(start=(0, 0), end=(scaled_width_mm, 0), 
                           stroke='gray', stroke_width=0.5))
            dwg.add(dwg.line(start=(0, 0), end=(0, scaled_height_mm), 
                           stroke='gray', stroke_width=0.5))
            
            self.draw_ruler(dwg, scaled_width_mm, self.scale_factor, axis='x', interval=10, size=2.5)
            self.draw_ruler(dwg, scaled_height_mm, self.scale_factor, axis='y', interval=10, size=2.5)
            
            # AGREGAR CONTORNOS
            for contour in contours:
                smoothed_contour = self.smooth_contour(contour, smooth_factor=0.5)
                points = [(x * self.pixel_to_mm * self.scale_factor, 
                            y * self.pixel_to_mm * self.scale_factor) 
                            for y, x in smoothed_contour]
                
                path_data = "M " + " L ".join([f"{x:.2f},{y:.2f}" for x, y in points]) + " Z"
                path = dwg.path(d=path_data, fill='none', stroke='black', stroke_width=0.3)
                dwg.add(path)
            
            dwg.save()
            return True
            
        except Exception as e:
            print(f"Error converting PNG to SVG: {e}")
            return False

    def svg_to_pdf(self, svg_path, pdf_path):
        """Convierte un archivo SVG a PDF."""
        try:
            cairosvg.svg2pdf(url=svg_path, write_to=pdf_path)
            return True
        except Exception as e:
            print(f"Error converting SVG to PDF: {e}")
            return False

    def create_svg_preview(self, svg_path):
        """Crea una imagen preview PNG del SVG para mostrar en la web."""
        try:
            png_data = cairosvg.svg2png(url=svg_path, output_width=300, output_height=400)
            return base64.b64encode(png_data).decode('utf-8')
        except Exception as e:
            print(f"Error creating SVG preview: {e}")
            return None

    def process_pattern_sizes(self, base_filename, skirt_type):
        try:
            # Rutas base
            static_path = os.path.join(os.getcwd(), 'static')
            tallas_path = os.path.join(static_path, 'tallas')
            patterns_path = os.path.join(static_path, 'patterns')
            
            # Crear directorio de patrones si no existe
            os.makedirs(patterns_path, exist_ok=True)
            
            results = {
                'success': False,
                'patterns': []
            }
            
            sizes = ['S', 'M', 'L']
            
            # Listar todos los archivos en static/tallas/ para depuración
            tallas_files = os.listdir(tallas_path)
            print(f"Archivos en {tallas_path}: {tallas_files}")
            
            for size in sizes:
                try:
                    # Buscar archivo de talla que coincida con el patrón size_[s/m/l]_{skirt_type}_*.png
                    pattern = f"size_{size.lower()}_{skirt_type}_*.png"
                    size_files = glob.glob(os.path.join(tallas_path, pattern))
                    
                    if not size_files:
                        print(f"No se encontraron archivos para: {pattern}")
                        continue
                    
                    # Tomar el archivo más reciente (en caso de que haya múltiples coincidencias)
                    size_image_path = max(size_files, key=os.path.getmtime)
                    size_filename = os.path.basename(size_image_path)
                    
                    print(f"Usando archivo de talla: {size_image_path}")
                    
                    # Generar nombres de archivos de salida
                    base_name = os.path.splitext(base_filename)[0]
                    svg_filename = f"{base_name}_pattern_{size.lower()}.svg"
                    pdf_filename = f"{base_name}_pattern_{size.lower()}.pdf"
                    
                    svg_path = os.path.join(patterns_path, svg_filename)
                    pdf_path = os.path.join(patterns_path, pdf_filename)
                    
                    # Convertir PNG a SVG
                    if self.png_to_svg(size_image_path, svg_path):
                        # Convertir SVG a PDF
                        if self.svg_to_pdf(svg_path, pdf_path):
                            # Crear preview
                            preview_base64 = self.create_svg_preview(svg_path)
                            
                            results['patterns'].append({
                                'size': size,
                                'svg_filename': svg_filename,
                                'pdf_filename': pdf_filename,
                                'preview_base64': preview_base64
                            })
                        else:
                            print(f"Error al convertir SVG a PDF para talla {size}")
                    else:
                        print(f"Error al convertir PNG a SVG para talla {size}")
                            
                except Exception as e:
                    print(f"Error procesando talla {size}: {e}")
                    continue
            
            if len(results['patterns']) > 0:
                results['success'] = True
                
            return results
            
        except Exception as e:
            print(f"Error general en process_pattern_sizes: {e}")
            return {'success': False, 'error': str(e)}
# Instancia global del servicio
pattern_service = PatternService()