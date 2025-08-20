from tensorflow.keras.models import load_model

model = load_model(r"D:\Models\Pneumonia\pneumonia_model.h5")

from tensorflow.keras.preprocessing import image
import numpy as np

# Path to your image
img_path = r"d:\Models\Database\Pneumonia\val\PNEUMONIA\person1954_bacteria_4886.jpeg"
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
    print("PREDICTION: PNEUMONIA")
else:
    print("PREDICTION: NORMAL")

# Optional: Show the actual probability
print(f"Probability: {prediction[0][0]:.4f}")

