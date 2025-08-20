from tensorflow.keras.models import load_model

model = load_model(r"C:\Users\athar\Downloads\SnapDx\SnapDx-new_auth\SnapDx-new_auth\AI_Models\Skin Cancer\skin_cancer_model.h5")

from tensorflow.keras.preprocessing import image
import numpy as np

# Path to your image
img_path = r"D:\Models\Database\Skin Cancer\train\CANCER\ISIC_0025376.jpg"
# Load image in grayscale mode and resize to model's input size
img = image.load_img(img_path, target_size=(150, 150), color_mode='grayscale')

# Convert to array
img_array = image.img_to_array(img)


# Reshape to match model input shape (1, 150, 150, 1)
img_array = np.expand_dims(img_array, axis=0)

# Normalize
img_array /= 255.0

prediction = model.predict(img_array)

# Since we used sigmoid activation: output is between 0 and 1
if prediction[0][0] > 0.5:
    print("PREDICTION: SKIN CANCER")
else:
    print("PREDICTION: NORMAL")

# Optional: Show the actual probability
print(f"Probability: {prediction[0][0]:.4f}")

