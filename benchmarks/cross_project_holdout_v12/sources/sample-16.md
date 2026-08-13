# Handwritten Digit Recognition
A neural network model for recognizing handwritten digits from the MNIST dataset, achieving 92.40% accuracy on training data and 89.87% during cross-validation.

## Description
In this project, a neural network was developed for recognizing handwritten digits using the MNIST dataset. The architecture of the network consists of one input layer, two hidden layers, and one output layer. The sigmoid activation function is applied in the hidden layers, while softmax is used in the output layer for multi-class classification.

The project includes data loading and preprocessing, including normalization of pixel values of the images and transforming them from matrices into vectors. The neural network is trained using stochastic gradient descent, and its performance is evaluated using metrics such as accuracy, F1-score, and ROC-AUC.

The project demonstrates good performance: the accuracy on training data was 92.40%, while on test data during cross-validation it was about 89.87%. The model shows a high ability to distinguish digits, recognizing 8-9 out of 10.
