import os
import torch
import numpy as np
from PIL import Image
from io import BytesIO
import base64
from diffusers import UNet2DModel, DDPMScheduler

device = "cuda" if torch.cuda.is_available() else "cpu"

DESIGN_MODELS = {
    'recta': 'checkpoint_design_recta.pth',
    'con_volante': 'checkpoint_design_con_volante.pth',
    'con_bolsillo': 'checkpoint_design_con_bolsillo.pth',
    'campana': 'checkpoint_design_campana.pth',
    'sirena': 'checkpoint_design_sirena.pth',
    'con_canesu': 'checkpoint_design_con_canesu.pth',
    'varios_disenos': 'checkpoint_design_varios_disenos.pth',
    'patrones_varios_disenos': 'checkpoint_design_patrones_varios_disenos.pth'
}

PATTERN_MODELS = {
    'recta': 'checkpoint_patron_recta.pth',
    'con_volante': 'checkpoint_patron_con_volante.pth',
    'con_bolsillo': 'checkpoint_patron_con_bolsillo.pth',
    'campana': 'checkpoint_patron_campana.pth',
    'sirena': 'checkpoint_patron_sirena.pth',
    'con_canesu': 'checkpoint_patron_con_canesu.pth',
    'varios_disenos': 'checkpoint_patron_varios_disenos.pth',
    'patrones_varios_disenos': 'checkpoint_patron_patrones_varios_disenos.pth'
}

def load_model(model_type, skirt_type):
    noise_scheduler = DDPMScheduler(
        num_train_timesteps=10,
        beta_schedule="linear",
        prediction_type="epsilon"
    )
    
    model = UNet2DModel(
        sample_size=(192, 128),
        in_channels=3,
        out_channels=3,
        layers_per_block=4,
        block_out_channels=(64, 128, 256, 256),
        down_block_types=("DownBlock2D", "DownBlock2D", "AttnDownBlock2D", "DownBlock2D"),
        up_block_types=("UpBlock2D", "AttnUpBlock2D", "UpBlock2D", "UpBlock2D")
    ).to(device)
    
    if model_type == 'design':
        checkpoint_filename = DESIGN_MODELS[skirt_type]
    else:
        checkpoint_filename = PATTERN_MODELS[skirt_type]
    
    checkpoint_path = os.path.join(os.path.dirname(__file__), '../models', checkpoint_filename)
    
    try:
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        return model, noise_scheduler
    except Exception as e:
        print(f"Error al cargar el modelo {checkpoint_filename}: {e}")
        return None, None

def generate_image(model_type, skirt_type):
    model, noise_scheduler = load_model(model_type, skirt_type)
    
    if model is None or noise_scheduler is None:
        return None
    
    with torch.no_grad():
        sample = torch.randn(1, 3, 192, 128).to(device)
        
        for t in range(noise_scheduler.config.num_train_timesteps - 1, -1, -1):
            model_output = model(sample, torch.tensor([t], device=device)).sample
            sample = noise_scheduler.step(model_output, t, sample).prev_sample
        
        img = (sample / 2 + 0.5).clamp(0, 1)
        img = img.cpu().permute(0, 2, 3, 1).numpy()
        img = (img * 255).astype(np.uint8)
        pil_img = Image.fromarray(img[0])
        
        filename = f"{model_type}_{skirt_type}_{int(torch.randint(0, 10000, (1,)).item())}.png"
        
        output_dir = os.path.join(os.path.dirname(__file__), '../static/downloads')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        pil_img.save(output_path)
        
        buffered = BytesIO()
        pil_img.save(buffered, format="PNG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return {
            'image_path': f'/static/downloads/{filename}',
            'image_base64': image_base64
        }

if __name__ == "__main__":
    result = generate_image('design', 'recta')
    if result:
        print(f"Imagen generada en: {result['image_path']}")
        print(f"Base64 generado: {result['image_base64'][:50]}...")
    else:
        print("Error al generar la imagen")