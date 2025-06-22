import os
import cv2
import numpy as np
import base64
from PIL import Image
from io import BytesIO
import time

def process_sizes(original_filename, skirt_type):
    """
    Procesa una imagen original para generar 3 tallas diferentes:
    - Talla S: Reducir 8 píxeles horizontalmente por la mitad
    - Talla M: Imagen original 
    - Talla L: Aumentar 8 píxeles horizontalmente por la mitad
    
    Args:
        original_filename (str): Nombre del archivo original
        skirt_type (str): Tipo de falda
    
    Returns:
        dict: Diccionario con las imágenes procesadas en base64 y rutas
    """
    
    try:
        # Configurar directorios
        downloads_dir = os.path.join('static', 'downloads')
        tallas_dir = os.path.join('static', 'tallas')
        
        # Crear directorio de tallas si no existe
        if not os.path.exists(tallas_dir):
            os.makedirs(tallas_dir)
        
        # Ruta de imagen original
        original_path = os.path.join(downloads_dir, original_filename)
        
        if not os.path.exists(original_path):
            print(f"Error: No se encontró el archivo {original_path}")
            return None
        
        # Cargar imagen original con OpenCV (128x192 píxeles)
        img_original = cv2.imread(original_path)
        if img_original is None:
            print(f"Error: No se pudo cargar la imagen {original_path}")
            return None
        
        height, width = img_original.shape[:2]
        print(f"Imagen original: {width}x{height} píxeles")
        
        # Generar timestamp para nombres únicos
        timestamp = int(time.time())
        
        # TALLA S: Reducir 8 píxeles por la mitad (120x192)
        size_s_img = generate_size_s(img_original)
        size_s_filename = f"size_s_{skirt_type}_{timestamp}.png"
        size_s_path = os.path.join(tallas_dir, size_s_filename)
        cv2.imwrite(size_s_path, size_s_img)
        
        # TALLA M: Imagen original (128x192)
        size_m_img = img_original.copy()
        size_m_filename = f"size_m_{skirt_type}_{timestamp}.png"
        size_m_path = os.path.join(tallas_dir, size_m_filename)
        cv2.imwrite(size_m_path, size_m_img)
        
        # TALLA L: Aumentar 8 píxeles por la mitad (136x192)
        size_l_img = generate_size_l(img_original)
        size_l_filename = f"size_l_{skirt_type}_{timestamp}.png"
        size_l_path = os.path.join(tallas_dir, size_l_filename)
        cv2.imwrite(size_l_path, size_l_img)
        
        # Convertir a base64
        size_s_base64 = image_to_base64(size_s_img)
        size_m_base64 = image_to_base64(size_m_img)
        size_l_base64 = image_to_base64(size_l_img)
        
        return {
            'size_s_base64': size_s_base64,
            'size_s_filename': size_s_filename,
            'size_s_path': f'/static/tallas/{size_s_filename}',
            
            'size_m_base64': size_m_base64,
            'size_m_filename': size_m_filename,
            'size_m_path': f'/static/tallas/{size_m_filename}',
            
            'size_l_base64': size_l_base64,
            'size_l_filename': size_l_filename,
            'size_l_path': f'/static/tallas/{size_l_filename}'
        }
        
    except Exception as e:
        print(f"Error procesando tallas: {e}")
        return None

def generate_size_s(img_original):
    """
    Genera talla S reduciendo 8 píxeles horizontalmente por la mitad.
    Mantiene la continuidad de los bordes superior e inferior.
    
    Args:
        img_original: Imagen OpenCV (128x192)
    
    Returns:
        np.array: Imagen procesada (120x192)
    """
    height, width = img_original.shape[:2]
    mid_point = width // 2  # punto 64
    
    # Dividir la imagen en dos mitades
    left_half = img_original[:, :mid_point]  # 0:64
    right_half = img_original[:, mid_point:]  # 64:128
    
    # Reducir cada mitad en 4 píxeles (total 8 píxeles)
    left_reduced = cv2.resize(left_half, (mid_point - 4, height), interpolation=cv2.INTER_LINEAR)
    right_reduced = cv2.resize(right_half, (mid_point - 4, height), interpolation=cv2.INTER_LINEAR)
    
    # Unir las mitades
    size_s_img = np.concatenate([left_reduced, right_reduced], axis=1)
    
    # Suavizar la unión en el centro para mantener continuidad
    size_s_img = smooth_center_join(size_s_img)
    
    return size_s_img

def generate_size_l(img_original):
    """
    Genera talla L aumentando 8 píxeles horizontalmente por la mitad.
    Clona píxeles para mantener la continuidad de los bordes.
    
    Args:
        img_original: Imagen OpenCV (128x192)
    
    Returns:
        np.array: Imagen procesada (136x192)
    """
    height, width = img_original.shape[:2]
    mid_point = width // 2  # punto 64
    
    # Dividir la imagen en dos mitades
    left_half = img_original[:, :mid_point]  # 0:64
    right_half = img_original[:, mid_point:]  # 64:128
    
    # Expandir cada mitad en 4 píxeles (total 8 píxeles)
    left_expanded = cv2.resize(left_half, (mid_point + 4, height), interpolation=cv2.INTER_LINEAR)
    right_expanded = cv2.resize(right_half, (mid_point + 4, height), interpolation=cv2.INTER_LINEAR)
    
    # Unir las mitades
    size_l_img = np.concatenate([left_expanded, right_expanded], axis=1)
    
    # Clonar píxeles en los bordes para mantener continuidad
    size_l_img = clone_edge_pixels(size_l_img)
    
    return size_l_img

def smooth_center_join(img):
    """
    Suaviza la unión en el centro de la imagen para talla S.
    
    Args:
        img: Imagen OpenCV
    
    Returns:
        np.array: Imagen con unión suavizada
    """
    height, width = img.shape[:2]
    center = width // 2
    
    # Crear una máscara de suavizado en el centro
    blend_width = 4  # píxeles a cada lado del centro
    
    if center - blend_width >= 0 and center + blend_width < width:
        for i in range(height):
            # Obtener valores de los píxeles adyacentes al centro
            left_pixels = img[i, center - blend_width:center]
            right_pixels = img[i, center:center + blend_width]
            
            # Crear transición suave
            for j in range(blend_width):
                alpha = j / blend_width
                img[i, center - blend_width + j] = (1 - alpha) * left_pixels[j] + alpha * left_pixels[-1]
                img[i, center + j] = (1 - alpha) * right_pixels[0] + alpha * right_pixels[j]
    
    return img

def clone_edge_pixels(img):
    """
    Clona píxeles en los bordes para mantener continuidad en talla L.
    
    Args:
        img: Imagen OpenCV
    
    Returns:
        np.array: Imagen con píxeles clonados
    """
    height, width = img.shape[:2]
    
    # Clonar píxeles superiores e inferiores para mantener forma del patrón
    clone_rows = 2
    
    # Clonar borde superior
    for i in range(clone_rows):
        img[i] = np.mean([img[i], img[clone_rows]], axis=0).astype(np.uint8)
    
    # Clonar borde inferior
    for i in range(height - clone_rows, height):
        img[i] = np.mean([img[i], img[height - clone_rows - 1]], axis=0).astype(np.uint8)
    
    # Suavizar bordes laterales
    smooth_width = 3
    for i in range(height):
        # Borde izquierdo
        for j in range(smooth_width):
            if j > 0:
                img[i, j] = (img[i, j] + img[i, j-1]) // 2
        
        # Borde derecho
        for j in range(width - smooth_width, width):
            if j < width - 1:
                img[i, j] = (img[i, j] + img[i, j+1]) // 2
    
    return img

def image_to_base64(img):
    """
    Convierte imagen OpenCV a base64.
    
    Args:
        img: Imagen OpenCV
    
    Returns:
        str: Imagen en formato base64
    """
    try:
        # Convertir de BGR a RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Convertir a PIL Image
        pil_img = Image.fromarray(img_rgb)
        
        # Convertir a base64
        buffered = BytesIO()
        pil_img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return img_base64
        
    except Exception as e:
        print(f"Error convirtiendo imagen a base64: {e}")
        return None

def get_size_info(size_type):
    """
    Obtiene información de tallas.
    
    Args:
        size_type (str): 's', 'm', o 'l'
    
    Returns:
        dict: Información de la talla
    """
    size_info = {
        's': {
            'name': 'Talla S',
            'hip_contour': '92 cm',
            'width': 120
        },
        'm': {
            'name': 'Talla M', 
            'hip_contour': '100 cm',
            'width': 128
        },
        'l': {
            'name': 'Talla L',
            'hip_contour': '108 cm', 
            'width': 136
        }
    }
    
    return size_info.get(size_type.lower(), size_info['m'])