# AI Disease Prediction System

## Overview
This system integrates AI models for disease prediction into the SnapDx platform. It supports three types of diseases:
- Pneumonia (Chest X-Ray analysis)
- Tuberculosis (Chest X-Ray analysis)
- Skin Cancer/Melanoma (Skin lesion analysis)

## Features

### 1. Disease Prediction
- **Multi-model Support**: Automatically selects the appropriate AI model based on disease type
- **Image Preprocessing**: Handles different image formats and preprocesses them for model input
- **Batch Processing**: Can analyze multiple images and provide aggregated results
- **Confidence Scoring**: Provides probability scores for predictions

### 2. Patient Management
- **Patient Registration**: Stores patient information in MongoDB
- **Diagnosis History**: Maintains complete diagnosis records
- **Report Generation**: Creates detailed medical reports with AI predictions

### 3. Database Collections

#### Patients Collection
```json
{
  "_id": "ObjectId",
  "name": "string",
  "age": "number",
  "gender": "string",
  "phone": "string",
  "created_by": "string (doctor email)",
  "created_at": "datetime"
}
```

#### Diagnoses Collection
```json
{
  "_id": "ObjectId",
  "patient_id": "ObjectId",
  "patient_name": "string",
  "disease_type": "string",
  "has_disease": "boolean",
  "probability": "number",
  "confidence_percentage": "number",
  "disease_name": "string",
  "total_images": "number",
  "individual_results": "array",
  "doctor_email": "string",
  "doctor_name": "string",
  "created_at": "datetime",
  "report_id": "string"
}
```

## API Endpoints

### POST /api/diagnose
Performs disease diagnosis using AI models.

**Request Body:**
```json
{
  "patient_name": "string",
  "patient_age": "number",
  "patient_gender": "string",
  "patient_phone": "string",
  "disease_type": "string (pneumonia|tuberculosis|melanoma)",
  "images": ["base64_encoded_image_data"]
}
```

**Response:**
```json
{
  "success": true,
  "diagnosis_id": "string",
  "patient_id": "string",
  "report_id": "string",
  "prediction": {
    "has_disease": "boolean",
    "disease_name": "string",
    "confidence_percentage": "number",
    "probability": "number"
  },
  "patient_info": "object",
  "timestamp": "string"
}
```

### GET /api/diagnoses
Retrieves all diagnoses for the logged-in doctor.

**Response:**
```json
{
  "success": true,
  "diagnoses": [
    {
      "_id": "string",
      "patient_id": "string",
      "patient_name": "string",
      "disease_type": "string",
      "has_disease": "boolean",
      "probability": "number",
      "confidence_percentage": "number",
      "disease_name": "string",
      "doctor_name": "string",
      "created_at": "string",
      "report_id": "string"
    }
  ]
}
```

## Model Requirements

### Model File Structure
```
AI_Models/
├── Pneumonia/
│   └── pneumonia_model.h5
├── Tuberculosis/
│   └── tuberculosis_model.h5
└── Skin Cancer/
    └── skin_cancer_model.h5
```

### Model Specifications
- **Input Size**: 150x150 pixels
- **Color Mode**: Grayscale
- **Output**: Binary classification (0-1 probability)
- **Threshold**: 0.5 for disease detection

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure model files are in the correct locations:
   - `AI_Models/Pneumonia/pneumonia_model.h5`
   - `AI_Models/Tuberculosis/tuberculosis_model.h5`
   - `AI_Models/Skin Cancer/skin_cancer_model.h5`

3. Run the application:
```bash
python main.py
```

## Usage

1. **Login as Doctor**: Access the doctor dashboard
2. **Navigate to Diagnose**: Go to the diagnosis page
3. **Select Disease Type**: Choose from Pneumonia, Tuberculosis, or Skin Cancer
4. **Enter Patient Information**: Fill in patient details
5. **Upload Images**: Upload medical images (X-Ray, skin photos, etc.)
6. **Generate Report**: Click "Generate Report" to get AI prediction
7. **View Results**: Review the generated report with AI analysis

## Error Handling

The system includes comprehensive error handling for:
- Missing model files
- Invalid image formats
- Database connection issues
- Authentication failures
- Prediction errors

## Security Features

- **Session-based Authentication**: Only logged-in doctors can access diagnosis features
- **Input Validation**: Validates all patient information and image data
- **Error Logging**: Logs errors for debugging without exposing sensitive information

## Performance Considerations

- **Model Loading**: Models are loaded once at startup for better performance
- **Image Preprocessing**: Efficient image processing pipeline
- **Batch Processing**: Supports multiple images for improved accuracy
- **Memory Management**: Proper cleanup of image data after processing
