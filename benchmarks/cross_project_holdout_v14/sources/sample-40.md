python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/more \
  --output-root probe_results \
  --train-stride 16 \
  --valid-stride 16 \
  --test-stride 16




python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/more/epoch_0002.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4


%%% to run 

for dir in checkpoints/jepa_vit_running/no_dropout checkpoints/jepa_vit_running/dropout; do
  PYTHONPATH=src python -m evaluation.run_probe \
    --checkpoint-dir "$dir" \
    --checkpoint-glob "*.pt" \
    --output-root probe_results \
    --train-stride 4 \
    --valid-stride 4 \
    --test-stride 4
done


### new for no dropout fast 

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/no_dropout \
  --output-root probe_results \
  --train-stride 16 \
  --valid-stride 16 \
  --test-stride 16


To run night Apr 28 

### only for best ones 

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/no_dropout/best \
  --output-root probe_results \
  --train-stride 1 \
  --valid-stride 1 \
  --test-stride 1

### complete with dropout (missing)

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout/missing \
  --output-root probe_results \
  --train-stride 16 \
  --valid-stride 16 \
  --test-stride 16


### (running) dropout on predictor only

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout_pred \
  --output-root probe_results \
  --train-stride 16 \
  --valid-stride 16 \
  --test-stride 16

The code: 

mkdir -p probe_logs

nohup bash -lc '
set -e
export PYTHONPATH=src

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout/missing/dropout_some \
  --output-root probe_results \
  --train-stride 16 \
  --valid-stride 16 \
  --test-stride 16 \
  > probe_logs/dropout_missing_stride16.log 2>&1

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout_pred \
  --output-root probe_results \
  --train-stride 16 \
  --valid-stride 16 \
  --test-stride 16 \
  > probe_logs/dropout_pred_stride16.log 2>&1

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/no_dropout/best \
  --output-root probe_results \
  --train-stride 1 \
  --valid-stride 1 \
  --test-stride 1 \
  > probe_logs/no_dropout_best_stride1.log 2>&1
' > probe_logs/all_probe_runs.log 2>&1 &



tail -f probe_logs/all_probe_runs.log

tail -f probe_logs/dropout_missing_stride16.log



tail -f probe_logs/dropout_missing_stride16.log
tail -f probe_logs/dropout_pred_stride16.log
tail -f probe_logs/no_dropout_best_stride1.log


To run night Apr 29 

## the best ones for dropout 


mkdir -p probe_logs

nohup bash -lc '
set -e
export PYTHONPATH=src

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout/missing/best_dropout \
  --output-root probe_results \
  --train-stride 1 \
  --valid-stride 1 \
  --test-stride 1 \
  > probe_logs/dropout_best1.log 2>&1

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout/missing/for_plot_dropout \
  --output-root probe_results \
  --train-stride 16 \
  --valid-stride 16 \
  --test-stride 16 \
  > probe_logs/for_plot_dropout16.log 2>&1

## full code with the attention thing 

cd /home/romina/DL_project

mkdir -p probe_logs attention_results

nohup bash -lc '
set -e
export PYTHONPATH=src

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout/missing/best_dropout \
  --output-root probe_results \
  --train-stride 1 \
  --valid-stride 1 \
  --test-stride 1 \
  > probe_logs/dropout_best1.log 2>&1

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout/missing/for_plot_dropout \
  --output-root probe_results \
  --train-stride 16 \
  --valid-stride 16 \
  --test-stride 16 \
  > probe_logs/for_plot_dropout16.log 2>&1

python -m evaluation.analyze_jepa_vit_field_attention \
  --checkpoint checkpoints/jepa_vit_running/dropout/best_model_rank_02.pt \
  --data-root /home/romina/DL_project \
  --split valid \
  --device cuda \
  --batch-size 4 \
  --output-dir attention_results/dropout_best_model_rank_02_valid \
  > probe_logs/attention_dropout_best_model_rank_02_valid.log 2>&1
' > probe_logs/dropout_probe_and_attention_driver.log 2>&1 &


## check with 
tail -f probe_logs/dropout_probe_and_attention_driver.log
tail -f probe_logs/dropout_best1.log
tail -f probe_logs/for_plot_dropout16.log
tail -f probe_logs/attention_dropout_best_model_rank_02_valid.log


### with new protocol on April 30

cd /home/romina/DL_project

mkdir -p probe_logs_f
probe_logs_f/physics_b128.log 
nohup bash -lc '
set -e
export PYTHONPATH=src

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/physics/top_five_physics \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  > probe_logs_f/physics_top.log 2>&1


python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout/top_five_dropout \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  > probe_logs_f/dropout_top.log 2>&1

python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/no_dropout/top_five_no_dropout \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  > probe_logs_f/no_dropout_top.log 2>&1
' > probe_logs_f/probe_driver.log 2>&1 &


### knn probing with cosine rather than euclidean and more runs 
cd /home/romina/DL_project

mkdir -p probe_logs_f

nohup bash -lc '
set -e
export PYTHONPATH=src

python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/dropout/top_five_dropout/best_model_rank_01.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  --probe-method knn \
  --knn-cosine \
  > probe_logs_f/dropout_cosine_01.log 2>&1

python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/dropout/top_five_dropout/best_model_rank_02.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  --probe-method knn \
  --knn-cosine \
  > probe_logs_f/dropout_cosine_02.log 2>&1

python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/dropout/top_five_dropout/best_model_rank_03.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  --probe-method knn \
  --knn-cosine \
  > probe_logs_f/dropout_cosine_03.log 2>&1

python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/physics/top_five_physics/best_model_rank_01.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  --probe-method knn \
  --knn-cosine \
  > probe_logs_f/physics_cosine_01.log 2>&1

python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/physics/top_five_physics/best_model_rank_02.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  --probe-method knn \
  --knn-cosine \
  > probe_logs_f/physics_cosine_02.log 2>&1


python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/physics/top_five_physics/best_model_rank_03.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  --probe-method knn \
  --knn-cosine \
  > probe_logs_f/physics_cosine_03.log 2>&1

python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/dropout/top_five_dropout/best_model_rank_04.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  > probe_logs_f/dropout_rank04.log 2>&1

python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/dropout/top_five_dropout/best_model_rank_05.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  > probe_logs_f/dropout_rank05.log 2>&1

python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/physics/top_five_physics/best_model_rank_04.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  > probe_logs_f/physics_rank04.log 2>&1

python -m evaluation.run_probe \
  --checkpoint checkpoints/jepa_vit_running/physics/top_five_physics/best_model_rank_05.pt \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  > probe_logs_f/physics_rank05.log 2>&1
' > probe_logs_f/all_probe_driver.log 2>&1 &


### latest runs with physics May 1

cd /home/romina/DL_project

mkdir -p probe_logs_f

nohup bash -lc '
set -e
export PYTHONPATH=src

./.venv/bin/python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/physics_b128 \
  --output-root probe_results \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  > probe_logs_f/physics_b128.log 2>&1
' > probe_logs_f/physics_b128_driver.log 2>&1 &


## May 1: run probes with the per-field pooling 


mkdir -p probe_logs_f

nohup bash -lc '
set -e
export PYTHONPATH=src

./.venv/bin/python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/physics_b128 \
  --feature-pool field \
  --knn-distance-metric cosine \
  --knn-min-k 3 \
  --knn-max-k 10 \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  --output-root probe_results \
  --output-folder physics_b128_field_pooling_stride4 \
  > probe_logs_f/physics_b128_field_pooling.log 2>&1

./.venv/bin/python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/dropout/top_five_dropout \
  --feature-pool field \
  --knn-distance-metric cosine \
  --knn-min-k 3 \
  --knn-max-k 10 \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  --output-root probe_results \
  --output-folder dropout_field_pooling_stride4 \
  > probe_logs_f/dropout_field_pooling.log 2>&1

./.venv/bin/python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/physics/top_five_physics \
  --feature-pool field \
  --knn-distance-metric cosine \
  --knn-min-k 3 \
  --knn-max-k 10 \
  --train-stride 4 \
  --valid-stride 4 \
  --test-stride 4 \
  --output-root probe_results \
  --output-folder physics_field_pooling_stride4 \
  > probe_logs_f/physics_field_pooling.log 2>&1

./.venv/bin/python -m evaluation.run_probe \
  --checkpoint-dir checkpoints/jepa_vit_running/physics_b128 \
  --feature-pool field \
  --knn-distance-metric cosine \
  --knn-min-k 3 \
  --knn-max-k 10 \
  --train-stride 2 \
  --valid-stride 2 \
  --test-stride 2 \
  --output-root probe_results \
  --output-folder physics_b128_field_pooling_stride2 \
  > probe_logs_f/physics_b128_field_pooling_stride2.log 2>&1
' > probe_logs_f/may_1.log 2>&1 &
