# Resumo — baselines, ablação de clima, GARCH e seleção de features

Protocolo comum: alvo log-retorno; walk-forward (5 folds, treino expansivo desde 50%); LOOKBACK=45, EMBARGO=45; StandardScaler por fold; LSTM avaliada como ensemble de N=5 sementes por fold.

## Tabela comparativa (nível/média)

| model                    |    RMSE |     MAE |   sMAPE |   MASE |   DirAcc |   DM_vs_naive |   DM_oos_vs_naive |   DM_oos_vs_ARIMA |   RMSE_seed_sd |
|:-------------------------|--------:|--------:|--------:|-------:|---------:|--------------:|------------------:|------------------:|---------------:|
| RandomWalk               | 0.02325 | 0.01814 |  198.45 |  0.724 |    0.008 |          0    |            nan    |            nan    |      nan       |
| ARIMA                    | 0.02325 | 0.01814 |  185.08 |  0.724 |    0.501 |         -0.2  |             -0.11 |            nan    |      nan       |
| LSTM_a_market            | 0.02356 | 0.01837 |  170.36 |  0.734 |    0.475 |          0.95 |              2.51 |              2.44 |        0.00018 |
| LSTM_b_market_climaRaw   | 0.02345 | 0.01836 |  163.99 |  0.733 |    0.502 |          0.54 |              1.12 |              1.13 |        0.00015 |
| LSTM_c_market_climaLag   | 0.02346 | 0.01829 |  168.74 |  0.73  |    0.493 |          0.6  |              1.55 |              1.64 |        0.00021 |
| LSTM_d_market_climaWprod | 0.02354 | 0.0184  |  171.39 |  0.735 |    0.46  |          0.8  |              1.62 |              1.65 |        0.00025 |

## Robustez a sementes — RMSE por config (N=5)

| model                    |    mean |     std |     min |     max |
|:-------------------------|--------:|--------:|--------:|--------:|
| LSTM_a_market            | 0.0237  | 0.00146 | 0.02211 | 0.02726 |
| LSTM_b_market_climaRaw   | 0.02367 | 0.00121 | 0.02215 | 0.02644 |
| LSTM_c_market_climaLag   | 0.02366 | 0.0014  | 0.02217 | 0.02661 |
| LSTM_d_market_climaWprod | 0.02366 | 0.00118 | 0.02227 | 0.02562 |

## GARCH(1,1) vs variância constante (QLIKE médio, menor = melhor)

- GARCH: -6.5081 | constante: -6.5181 (GARCH vence em 2/5 folds)

## Estabilidade da seleção (fração de folds no top-12)

|                           |   freq_top12 |
|:--------------------------|-------------:|
| ret_cafe                  |          1   |
| sma_10                    |          1   |
| vol_5                     |          1   |
| umidade_pct_mean_Manhuacu |          1   |
| ret_cambio                |          1   |
| vol_21                    |          1   |
| sin_doy                   |          1   |
| temp_ar_C_mean_Patrocinio |          0.8 |
| precip_mm_sum_Manhuacu    |          0.8 |
| umidade_pct_mean_Machado  |          0.8 |
| temp_min_C_min_Patrocinio |          0.6 |
| cos_doy                   |          0.6 |

## Veredito

- **Melhor LSTM**: LSTM_b_market_climaRaw (RMSE 0.02345 ± 0.00015).
- **vs random walk** (RMSE 0.02325): DM_oos = 1.12 (sem diferença significativa).
- **vs ARIMA** (RMSE 0.02325): DM_oos = 1.13 (sem diferença significativa).
- **Clima ajuda?** RMSE: só-mercado 0.02356 | +clima bruto 0.02345 | +clima defasado 0.02346.
  → adicionar clima (bruto) **reduziu** o RMSE médio (efeito pequeno; ver robustez).
- **Granularidade regional (B vs C)**: por cidade 0.02345 vs ponderado 0.02354 → melhor: por cidade (Opção B).
- **Robustez a sementes (N=5)**: dispersão entre sementes ~0.00020 (sd) vs espalhamento entre configs ~0.00011 → as diferenças entre configs estão na MESMA ORDEM do ruído de semente — interpretar o ganho do clima com cautela.
- **Volatilidade (GARCH vs variância constante)**: QLIKE -6.508 vs -6.518 (GARCH vence 2/5 folds) → sem ganho consistente do GARCH.
