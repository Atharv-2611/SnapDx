import os
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from PIL import Image
import io
import base64

class DiseasePredictor:
    def __init__(self):
        # Define model paths
        self.model_paths = {
            'pneumonia': 'AI_Models/Pneumonia/pneumonia_model.h5',
            'tuberculosis': 'AI_Models/Tuberculosis/tuberculosis_model.h5',
            'melanoma': 'AI_Models/Skin Cancer/skin_cancer_model.h5'
        }
        
        # Load models
        self.models = {}
        for disease, path in self.model_paths.items():
            if os.path.exists(path):
                try:
                    self.models[disease] = load_model(path)
                    print(f"Loaded {disease} model successfully")
                except Exception as e:
                    print(f"Error loading {disease} model: {e}")
            else:
                print(f"Model file not found: {path}")
    
    def preprocess_image(self, image_file, disease_type):
        """Preprocess image based on disease type requirements"""
        try:
            # Convert file to PIL Image
            if isinstance(image_file, str):
                # If it's a base64 string
                if image_file.startswith('data:image'):
                    # Remove data URL prefix
                    image_data = image_file.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                    img = Image.open(io.BytesIO(image_bytes))
                else:
                    # If it's a file path
                    img = Image.open(image_file)
            else:
                # If it's a file object
                img = Image.open(image_file)
            
            # Convert to grayscale for medical images
            if disease_type in ['pneumonia', 'tuberculosis']:
                img = img.convert('L')  # Grayscale
            elif disease_type == 'melanoma':
                # For skin cancer, we might want to keep color or convert to grayscale
                # Based on the training data, let's use grayscale
                img = img.convert('L')
            
            # Resize to 150x150 (standard size for our models)
            img = img.resize((150, 150))
            
            # Convert to array and normalize
            img_array = image.img_to_array(img)
            img_array = img_array / 255.0
            
            # Add batch dimension
            img_array = np.expand_dims(img_array, axis=0)
            
            return img_array
            
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return None
    
    def predict_disease(self, image_file, disease_type):
        """Predict disease based on image and disease type"""
        try:
            if disease_type not in self.models:
                return {
                    'success': False,
                    'error': f'Model for {disease_type} not available'
                }
            
            # Preprocess image
            processed_image = self.preprocess_image(image_file, disease_type)
            if processed_image is None:
                return {
                    'success': False,
                    'error': 'Failed to preprocess image'
                }
            
            # Make prediction
            model = self.models[disease_type]
            prediction = model.predict(processed_image)
            
            # Get probability
            probability = float(prediction[0][0])
            
            # Determine result based on disease type
            if disease_type == 'pneumonia':
                has_disease = probability > 0.5
                disease_name = 'Pneumonia' if has_disease else 'Normal'
            elif disease_type == 'tuberculosis':
                has_disease = probability > 0.5
                disease_name = 'Tuberculosis' if has_disease else 'Normal'
            elif disease_type == 'melanoma':
                has_disease = probability > 0.5
                disease_name = 'Melanoma' if has_disease else 'Benign'
            
            return {
                'success': True,
                'has_disease': bool(has_disease),
                'probability': float(probability),
                'disease_name': disease_name,
                'confidence_percentage': round(float(probability) * 100, 2)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Prediction error: {str(e)}'
            }
    
    def predict_multiple_images(self, image_files, disease_type):
        """Predict disease for multiple images and return aggregated result"""
        if not image_files:
            return {
                'success': False,
                'error': 'No images provided'
            }
        
        results = []
        for img_file in image_files:
            result = self.predict_disease(img_file, disease_type)
            if result['success']:
                results.append(result)
        
        if not results:
            return {
                'success': False,
                'error': 'No successful predictions'
            }
        
        # Aggregate results
        avg_probability = np.mean([r['probability'] for r in results])
        has_disease = avg_probability > 0.5
        
        # Determine disease name
        if disease_type == 'pneumonia':
            disease_name = 'Pneumonia' if has_disease else 'Normal'
        elif disease_type == 'tuberculosis':
            disease_name = 'Tuberculosis' if has_disease else 'Normal'
        elif disease_type == 'melanoma':
            disease_name = 'Melanoma' if has_disease else 'Benign'
        
        return {
            'success': True,
            'has_disease': bool(has_disease),
            'probability': float(avg_probability),
            'disease_name': disease_name,
            'confidence_percentage': round(float(avg_probability) * 100, 2),
            'individual_results': results,
            'total_images': len(image_files)
        }

# Global predictor instance
predictor = DiseasePredictor()
