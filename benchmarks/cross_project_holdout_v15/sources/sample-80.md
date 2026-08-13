
# Final Solution Report


## Introduction
This assignment's primary objective was to develop a model for changing a toxic statement into a detoxic one while maintaining the phrase's meaning. Additionally, if the language wasn't poisonous in the first place, it was important to confirm that it wasn't and to leave it alone. There are many different solutions to this problem, however I decided to use a solution using Seq2Seq models as shown in the lab. I used the following models in my work: deletion of toxic words, Bert, T5-base, fine-tuned T5 and Bart models.

## Data Analysis

To train and test my models, a ParaNMT dataset was used, which includes reference and translation sentence pairs with the toxicity level of their text. I changed the dataset to make it easier to work with. I changed the following:

* Changed the dataset columns from reference and translation to toxic and nontoxic, leaving the toxic_tox and nontoxic_tox columns.

* I removed the other columns because I couldn't think of a way to apply them to the task at hand

* Many of the toxic and nontoxic columns contained low levels of toxic_tox and nontoxic_tox, so I removed those data in which toxic_tox < 75% and nontoxic_tox > 25%.

## Model Specification

I used the following models:

1.  Baseline: For baseline, I decided to use a classifier that can be used to identify toxic words to then remove them. Using the s-nlp/roberta_toxicity_toxicity_classifier_v1 model, I determine the toxicity probabilities of words to remove words with a high probability of toxicity from the dataset. This model works well, however it does not replace words in sentences, due to which the sentence may lose meaning.
    
2.  Text-To-Text Transfer Transformer (T5-base): A combination of supervised and unsupervised tasks were used to pre-train the encoder-decoder model T5, which was then trained on each task using a text-to-text format. T5 applies an appropriate prefix to the input according to the job, which allows it to perform effectively on a wide range of tasks straight out of the box. When using corrupted tokens for self-supervised training, 15% of the tokens are randomly removed and replaced with unique sentinel tokens (if many consecutive tokens are designated for removal, the entire group is replaced with a single sentinel token). The original sentence is the input of the decoder, the corrupted sentence is the input of the encoder, and the dropped out tokens are the target, separated by their sentinel tokens. Relative scalar embeddings are used in T5. Padding encoder input can be done both to the left and to the right.
    
3.  Fine-tuned T5: To improve the model results, I used a fine-tuned model for text detoxification tasks. The s-nlp/t5-paranmt-detox is suitable for my task, so I fine-tuned this model at 15 epochs and then saved it in the `models` folder.
    
4.  Pre-trained Bart: Initially text is corrupted using an arbitrary noising function, and then BART is pre-trained by building a model to reconstruct the original text. It makes use of a conventional Transformer-based neural machine translation architecture, which, in spite of its simplicity, may be understood as a generalization of many other more current pre-training schemes as well as BERT, GPT, and left-to-right decoder-based pre-training schemes. I used pre-trained s-nlp/bart-base-detox, fine-tuned it at 5 epochs and then also saved my model to the `models` folder.

## Training process

Due to the fact that the models I used are very large, it was impossible to train them on the entire dataset (not enough time and power). Therefore, I used only a part of the dataset (for some models up to 10000 words, for some up to 70000 instances).

For the sequence-to-sequence detoxification challenge, I used the Seq2SeqTrainer. In most cases, measures like ROUGE, TER, or BLEU are assessed for such generative tasks. Nevertheless, these metrics need that we produce some text using the model instead of just one forward pass like in classification, for example. When predict_with_generate=True, the Seq2SeqTrainer permits the usage of the generate method, which produces text for each sample in the evaluation set. This indicates that the compute_metric function is where we assess created text. All we have to do is first decode the labels and predictions.

## Evaluation

For evaluating my models I used the following metrics:

  

1.  BLEU (Bilingual Evaluation Understudy):

* BLEU is a metric that measures the similarity between a generated text and one or more reference texts.
* It is used to assess the quality of machine-generated text by comparing it to human-written reference text.
* BLEU measures precision, i.e., how many of the generated n-grams (contiguous sequences of words) appear in the reference text.

  

2.  TER (Translation Edit Rate):
    
* It measures the number of edits (insertions, deletions, substitutions) required to transform the generated text into the reference text.
* The lower the TER score, the more similar the generated text is to the reference text.
* TER is typically used to evaluate the fluency and accuracy of machine-generated text.

  

3.  ROUGE (Recall-Oriented Understudy for Gisting Evaluation):
    
* ROUGE includes several variants, such as ROUGE-1 (unigram overlap) and ROUGE-2 (bigram overlap), which measure the overlap of n-grams between the generated text and reference text.
* ROUGE metrics are based on recall, focusing on the recall of n-grams from the reference text in the generated text.


## Results

| Model/Metric  | Average BLEU | Average TER | Average ROUGE1 F1 | Average ROUGE2 F1 | Gen Len   |
|---------------|--------------|-------------|-------------------|-------------------|-----------|
| T5            | 21.073064    | 66.6632716  | 0.5487314         | 0.31443           | 13.395    |
| Fine-tuned T5 | 26.2724224   | 61.1543288  | 0.5945896         | 0.37347           | 12.7958   |
| Bart          | 24.8999908   | 62.6516132  | 0.5844694         | 0.3625184         | 20.000000 |

input: It was perfectly planned, but stupidly done. \\
baseline: It was perfectly planned, but done. \\
bert: it was perfectly planned, but expertly done.. \\
bart: It was perfectly planned and horribly done. \\
T5: It was perfectly planned, but it was a waste of time.

As we see, the metrics are still far from perfect, but looking at the translated test sentences, we can say that all models perform well in detoxifying sentences. 

*I used only part of the dataset (about 10-15%) because I didn't have a powerful gpu to handle the whole dataset. I used google colab to train and test my models, but still did not get high speed in model training.
