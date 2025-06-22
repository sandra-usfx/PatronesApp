import os
from flask import Blueprint, render_template, request, jsonify, send_from_directory, send_file
from services.diffusion_service import generate_image
from services.size_service import process_sizes
from services.pattern_service import pattern_service

# Crear la variable routes
routes = Blueprint('routes', __name__)

# Configuración de directorios
DOWNLOADS_DIR = os.path.join('static', 'downloads')
TALLAS_DIR = os.path.join('static', 'tallas')

# Crear directorios si no existen
for directory in [DOWNLOADS_DIR, TALLAS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

@routes.route('/', methods=['GET'])
def index():
    """Página principal"""
    return render_template('index.html')

@routes.route('/api/generate', methods=['POST'])
def api_generate():
    """Endpoint principal para generar imágenes"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
        
        model_type = data.get('model_type')
        skirt_type = data.get('skirt_type')
        
        print(f"Generando: {model_type} - {skirt_type}")
        
        # VALIDAR DATOS
        valid_types = ['recta', 'con_volante', 'con_bolsillo', 'campana', 'sirena', 'con_canesu', 'varios_disenos', 'patrones_varios_disenos']
        valid_models = ['design', 'pattern']
        
        if skirt_type not in valid_types:
            return jsonify({'success': False, 'error': f'Tipo de falda inválido: {skirt_type}'}), 400
        if model_type not in valid_models:
            return jsonify({'success': False, 'error': f'Tipo de modelo inválido: {model_type}'}), 400
        
        result = generate_image(model_type, skirt_type)
        if not result:
            return jsonify({'success': False, 'error': 'Error al generar la imagen'}), 500
        
        return jsonify({
            'success': True,
            'image_base64': result['image_base64'],
            'image_url': result['image_path'],
            'model_type': model_type,
            'skirt_type': skirt_type
        })
            
    except Exception as e:
        print(f"Error en api_generate: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@routes.route('/api/generate_sizes', methods=['POST'])
def api_generate_sizes():
    """Endpoint para generar tallas de un patrón existente"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
        
        filename = data.get('filename')
        skirt_type = data.get('skirt_type')
        
        if not filename:
            return jsonify({'success': False, 'error': 'Nombre de archivo no proporcionado'}), 400
        
        if not skirt_type:
            return jsonify({'success': False, 'error': 'Tipo de falda no proporcionado'}), 400
        
        print(f"Generando tallas para: {filename} - {skirt_type}")
        
        # Verificar si el archivo existe
        original_path = os.path.join(DOWNLOADS_DIR, filename)
        if not os.path.exists(original_path):
            return jsonify({'success': False, 'error': f'Archivo no encontrado: {filename}'}), 404
        
        # Procesar tallas localmente
        print("Procesando tallas localmente...")
        sizes_result = process_sizes(filename, skirt_type)
        if not sizes_result:
            return jsonify({'success': False, 'error': 'Error al procesar las tallas'}), 500
        
        return jsonify({
            'success': True,
            'size_s_base64': sizes_result['size_s_base64'],
            'size_s_filename': sizes_result['size_s_filename'],
            'size_m_base64': sizes_result['size_m_base64'],
            'size_m_filename': sizes_result['size_m_filename'],
            'size_l_base64': sizes_result['size_l_base64'],
            'size_l_filename': sizes_result['size_l_filename']
        })
            
    except Exception as e:
        print(f"Error en api_generate_sizes: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@routes.route('/api/generate_patterns', methods=['POST'])
def generate_patterns():
    """Endpoint para generar patrones PDF"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        skirt_type = data.get('skirt_type')
        
        if not filename:
            return jsonify({'success': False, 'error': 'Filename requerido'}), 400
        
        if not skirt_type:
            return jsonify({'success': False, 'error': 'Tipo de falda no proporcionado'}), 400
        
        print(f"Procesando patrones para: {filename} - {skirt_type}")
        
        # Verificar si el archivo base existe
        base_path = os.path.join(DOWNLOADS_DIR, filename)
        if not os.path.exists(base_path):
            print(f"Archivo base no encontrado: {base_path}")
            return jsonify({'success': False, 'error': f'Archivo base no encontrado: {filename}'}), 404
        
        # Listar archivos en static/tallas/ para depuración
        tallas_files = os.listdir(TALLAS_DIR)
        print(f"Archivos en {TALLAS_DIR}: {tallas_files}")
        
        # Procesar las tallas y generar patrones
        result = pattern_service.process_pattern_sizes(filename, skirt_type)
        
        if result['success']:
            response_data = {
                'success': True,
                'pattern_s_preview': None,
                'pattern_s_filename': None,
                'pattern_m_preview': None, 
                'pattern_m_filename': None,
                'pattern_l_preview': None,
                'pattern_l_filename': None
            }
            
            # Organizar los datos por talla
            for pattern in result['patterns']:
                size = pattern['size'].lower()
                response_data[f'pattern_{size}_preview'] = pattern['preview_base64']
                response_data[f'pattern_{size}_filename'] = pattern['pdf_filename']
            
            return jsonify(response_data)
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Error procesando patrones')})
            
    except Exception as e:
        print(f"Error en generate_patterns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@routes.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    """Descargar archivos generados"""
    try:
        return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Archivo no encontrado'}), 404

@routes.route('/tallas/<filename>', methods=['GET'])
def download_size_file(filename):
    """Descargar archivos de tallas"""
    try:
        return send_from_directory(TALLAS_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Archivo de talla no encontrado'}), 404

@routes.route('/patterns/<filename>')
def download_pattern(filename):
    """Ruta para descargar archivos PDF de patrones"""
    try:
        patterns_path = os.path.join(os.getcwd(), 'static', 'patterns')
        file_path = os.path.join(patterns_path, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': 'Archivo no encontrado'}), 404
            
    except Exception as e:
        print(f"Error descargando patrón: {e}")
        return jsonify({'error': str(e)}), 500

@routes.route('/generate_design/<skirt_type>', methods=['GET'])
def generate_design(skirt_type):
    """Generar diseño (endpoint GET para compatibilidad)"""
    valid_types = ['recta', 'con_volante', 'con_bolsillo', 'campana', 'sirena', 'con_canesu', 'varios_disenos', 'patrones_varios_disenos']
    if skirt_type not in valid_types:
        return render_template('index.html', error=f'Tipo de falda inválido: {skirt_type}')
    
    try:
        result = generate_image('design', skirt_type)
        if not result:
            return render_template('index.html', error='Error al generar el diseño')
        
        return render_template('design_result.html', 
                              image_path=result['image_path'], 
                              skirt_type=skirt_type)
                              
    except Exception as e:
        return render_template('index.html', error=f'Error al generar el diseño: {str(e)}')

@routes.route('/generate_pattern/<skirt_type>', methods=['GET'])
def generate_pattern(skirt_type):
    """Generar patrón (endpoint GET para compatibilidad)"""
    valid_types = ['recta', 'con_volante', 'con_bolsillo', 'campana', 'sirena', 'con_canesu', 'varios_disenos', 'patrones_varios_disenos']
    if skirt_type not in valid_types:
        return render_template('index.html', error=f'Tipo de falda inválido: {skirt_type}')
    
    try:
        result = generate_image('pattern', skirt_type)
        if not result:
            return render_template('index.html', error='Error al generar el patrón')
        
        return render_template('pattern_result.html', 
                              image_path=result['image_path'], 
                              skirt_type=skirt_type)
                              
    except Exception as e:
        return render_template('index.html', error=f'Error al generar el patrón: {str(e)}')

@routes.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'environment': 'local'
    })