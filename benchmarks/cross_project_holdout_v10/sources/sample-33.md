# 🍫 Chocolate Recognition with Deep Learning
## IAPR 2025 Final Project - Group 1

A computer vision system for automated chocolate detection and classification using deep learning, achieving ~87% accuracy on the Kaggle leaderboard.

## 📋 Project Overview

This project tackles the challenging task of automatically detecting and counting 13 different types of chocolates in high-resolution images. We implemented a two-stage deep learning pipeline:

1. **U-Net** for chocolate segmentation (localization)
2. **CNN** for chocolate type classification

### 🎯 Key Achievements
- **99.5%** classification accuracy on individual chocolates
- **99.2%** ROC AUC for segmentation performance  
- **87%** end-to-end system accuracy on test set
- Fully automated pipeline from raw images to submission file

## 👥 Team Members
- **Alessio Zazo** 
- **Gautier Demierre** 
- **Georg Schwabedal** 

## 🏆 Competition Details

**Track:** Deep Learning (Machine Learning Track)  
**Platform:** Kaggle - [Chocolate Recognition ML](https://www.kaggle.com/competitions/chocolate-recognition-ml)  
**Kaggle Team:** group 1

## 🚀 Quick Start

### Environment Setup

Using conda (recommended):
```bash
conda env create -f environment.yml
conda activate iapr_project
```

Using pip:
```bash
pip install -r requirements.txt
```

### Generate Submission

To reproduce our Kaggle submission:
```bash
python main.py
```

This will generate `submission.csv` with chocolate counts for all 180 test images.

### Verify Submission

Check submission validity:
```bash
python check.py check --path submission.csv
```

Compare with Kaggle submission:
```bash
python check.py match --local submission.csv --kaggle kaggle.csv
```

## 📁 Project Structure

```
📦 chocolate-recognition/
├── 📄 main.py                 # Main pipeline - generates submission.csv
├── 📄 check.py                # Submission validation tool
├── 📄 report.ipynb            # Detailed project report with visualizations
├── 📄 report.pdf              # PDF version of the report
├── 📄 environment.yml         # Conda environment configuration
├── 📄 requirements.txt        # Python dependencies
├── 📄 sample_submission.csv   # Submission format example
├── 📄 submission.csv          # Generated predictions (after running main.py)
│
└── 📁 src/                    # Source code and data
    ├── 📁 models/             # Trained model weights
    │   ├── 📁 UNET/          
    │   │   └── unet_final.pth           # U-Net segmentation model
    │   └── 📁 CNN/           
    │       └── chocolate_classifier_final.pth  # CNN classifier
    │
    ├── 📁 data/               # Datasets and annotations
    │   ├── 📁 dataset_project_iapr2025/  # Original dataset
    │   │   ├── 📁 train/                 # 90 training images
    │   │   ├── 📁 test/                  # 180 test images
    │   │   └── 📁 reference_images/      # 13 chocolate references
    │   │
    │   ├── 📁 synthetic_UNET/   # Generated training data for U-Net
    │   │   ├── 📁 images/       # 1000 synthetic images
    │   │   └── 📁 masks/        # Corresponding binary masks
    │   │
    │   ├── 📁 synthetic_CNN/    # Generated patches for CNN
    │   │   └── [13,000 chocolate patches, 1000 per class]
    │   │
    │   └── labels_mask_ai.json  # Manual COCO annotations
    │
    └── 📁 utils/              # Helper functions
        ├── data_preparation.py
        ├── model_architectures.py
        └── inference.py
```

## 🔬 Methodology

### 1. Data Preparation
- **Manual Annotation**: 90 training images annotated using Mask AI platform
- **Synthetic Data Generation**: 
  - 1,000 synthetic images for U-Net training
  - 13,000 chocolate patches (1,000 per class) for CNN training
- **Data Augmentation**: Random rotations and placements

### 2. Model Architecture

#### U-Net (Segmentation)
- **Architecture**: 4-level encoder-decoder with skip connections
- **Input**: 256×256 RGB images
- **Output**: Binary segmentation masks
- **Parameters**: 7.8M
- **Performance**: IoU = 0.90, Dice = 0.95

#### CNN (Classification)  
- **Architecture**: 4 convolutional blocks + 2 FC layers
- **Input**: 224×224 chocolate patches
- **Output**: 13-class predictions
- **Performance**: 99.5% accuracy

### 3. Inference Pipeline

```python
Test Image → U-Net Segmentation → Blob Detection → 
Splitting Algorithm → Patch Extraction → CNN Classification → 
Chocolate Counting → Submission File
```

Key components:
- **Blob Splitting**: Custom algorithm to separate touching chocolates
- **Convexity Analysis**: Identifies and splits merged chocolates
- **High-Resolution Processing**: Maintains detail for classification

## 📊 Performance Metrics

### Segmentation (U-Net)
| Metric | Score |
|--------|-------|
| IoU | 0.90 |
| Dice | 0.95 |
| Precision | 0.92 |
| Recall | 0.97 |
| ROC AUC | 0.99 |

### Classification (CNN)
| Metric | Score |
|--------|-------|
| Accuracy | 99.50% |
| Precision | 99.52% |
| Recall | 99.47% |
| F1-Score | 99.48% |

### End-to-End System
- **Public Leaderboard**: ~87% accuracy
- **Main Challenge**: Blob splitting for touching chocolates

## 🍫 Chocolate Classes

The 13 chocolate varieties we classify:
1. Jelly White
2. Jelly Milk  
3. Jelly Black
4. Amandina
5. Crème brulée
6. Triangolo
7. Tentation noir
8. Comtesse
9. Noblesse
10. Noir authentique
11. Passion au lait
12. Arabia
13. Stracciatella

## ⚙️ Technical Requirements

- Python 3.9.x
- PyTorch with CUDA support (recommended)
- 8GB+ RAM
- GPU with 4GB+ VRAM (optional but recommended)

Key dependencies:
- torch, torchvision
- numpy, pandas
- opencv-python, PIL
- scikit-learn, scipy
- matplotlib, seaborn

## 🎓 Learning Outcomes

This project demonstrated:
- **Integration Challenges**: Individual component excellence doesn't guarantee system-level performance
- **Edge Cases Matter**: Handling touching chocolates proved critical
- **Trade-offs**: Balance between processing efficiency (256×256) and detail preservation
- **Data Generation**: Synthetic data effectively augmented limited training samples

## 🔮 Future Improvements

1. **Advanced Segmentation**: Instance segmentation (Mask R-CNN) instead of semantic segmentation
2. **Better Splitting**: Machine learning-based chocolate separation
3. **Higher Resolution**: Process at original resolution despite computational cost
4. **End-to-End Training**: Joint optimization of detection and classification
5. **Post-Processing**: Validation layer to filter false positives

## 📚 References

- Original U-Net paper: [Ronneberger et al., 2015](https://arxiv.org/abs/1505.04597)
- Instance Segmentation: [Mask R-CNN](https://arxiv.org/abs/1703.06870)
- COCO Format: [COCO Dataset](https://cocodataset.org/#format-data)

## 📝 Notes

- The complete pipeline takes ~30 minutes to process all test images
- Pre-trained weights are included for reproducibility
- Training from scratch requires ~2-3 hours on GPU
- Manual annotations available in COCO format

## 🤝 Acknowledgments

- EPFL IAPR Course Team for project organization
- Mask AI platform for annotation tools
- Kaggle for hosting the competition

---

*For detailed implementation and results, please refer to `report.ipynb` or `report.pdf`*