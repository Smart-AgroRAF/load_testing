# SmartAgroRAF Load Testing Tool

Este repositório contém uma ferramenta de teste de carga personalizada para avaliar o desempenho da plataforma SmartAgroRAF, focando em interações com Blockchain (Besu) e API.

## 📂 Estrutura do Projeto

O projeto é modularizado para separar a orquestração, definição de comportamento de usuário, execução de baixo nível e análise de dados.

### Componentes Principais

*   **`main.py`**:  
    O ponto de entrada da aplicação. Responsável por:
    *   Ler os argumentos da linha de comando (usuários, duração, contrato, modo).
    *   Configurar o ambiente e logs.
    *   Orquestrar a execução chamando o `LoadTester`.
    *   Gerar estatísticas finais e chamar o módulo de salvamento.

*   **`load_tester.py`**:  
    O coração da execução. A classe `LoadTester`:
    *   Gerencia o pool de threads (`ThreadPoolExecutor`) para simular usuários concorrentes.
    *   Controla os modos de teste: **Static** (carga constante) e **Ramp-up** (aumento gradual de usuários).
    *   Coleta os resultados brutos de cada "usuário".

*   **`users/`**:  
    Define o comportamento dos usuários virtuais.
    *   `User`: Classe base que contém a lógica de "campanhas" (sequências de ações).
    *   `UserERC721` / `UserERC1155`: Especializações para diferentes tipos de contrato.
    *   Cada usuário possui sua própria carteira (`Wallet`) e contadores de métricas.

*   **`tasks/`**:  
    Camada de execução de baixo nível.
    *   `TaskAPI`: Realiza chamadas HTTP para a API.
    *   `TaskBlockchain`: Constrói, assina e envia transações para a rede blockchain usando `web3.py`.

*   **`save.py`**:  
    Responsável pela persistência de dados.
    *   `save_all_outputs`: Função central que salva os resultados brutos, resumo global e estatísticas detalhadas.

*   **`stats.py`**:  
    Módulo de cálculo estatístico.
    *   A classe `Stats` processa os CSVs brutos para calcular média, mediana, percentis (P50, P90, P99) e RPS (Requests Per Second).

*   **`plot.py`**:  
    Módulo de geração de gráficos.
    *   Gera automaticamente visualizações comparativas a partir dos dados coletados.
    *   Produz gráficos de latência, vazão (throughput), contagem de requisições e análise detalhada de transações blockchain.

*   **`config.py`**:  
    Variáveis de ambiente, URLs da API/RPC e configurações globais.

## 🚀 Como Executar

O script é executado via linha de comando. Exemplo básico:

```bash
python3 main.py --users 10 --duration 60 --run static --contract erc721
```

## 📋 Parâmetros Disponíveis

### Configuração Geral

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `--verbosity`, `-v` | int | 20 (INFO) | Nível de verbosidade do log (INFO=20, DEBUG=10) |
| `--plot` | str | - | Gera gráficos a partir dos arquivos CSV de resultados existentes (caminho do diretório) |

### Configuração de Teste

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `--mode` | str | `api-blockchain` | Modo de execução (definido em `config.py`) |
| `--type` | str | `paired` | Modo de combinação dos parâmetros: `cartesian` (produto cartesiano) ou `paired` (pareamento 1:1) |
| `--contract` | str | `both` | Padrão de contrato: `erc721`, `erc1155` ou `both` |
| `--run` | str | `both` | Tipo de execução: `static`, `ramp-up` ou `both` |
| `--host` | str | (config) | Host alvo da API/RPC |

### Parâmetros Principais de Carga

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `--duration` | float[] | [60.0] | Duração do teste em segundos (aceita múltiplos valores) |
| `--users` | int[] | [10] | Número de usuários simultâneos (aceita múltiplos valores) |
| `--step-users` | int[] | [1] | Número de usuários adicionados a cada incremento (modo ramp-up) |
| `--interval-users` | float[] | [1.0] | Tempo entre incrementos de usuários em segundos (modo ramp-up) |
| `--interval-requests` | float | 1.0 | Pausa entre requisições consecutivas do mesmo usuário (em segundos) |

### Parâmetros de Warm-up

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `--warmup-users` | int | 1 | Número de usuários no warm-up |
| `--warmup-duration` | float | 0 | Duração do warm-up em segundos (0 = desabilitado) |
| `--warmup-step-users` | int | 1 | Incremento de usuários no warm-up |
| `--warmup-interval-users` | float | 1.0 | Tempo entre incrementos no warm-up (segundos) |
| `--warmup-interval-requests` | float | 1.0 | Pausa entre requisições no warm-up (segundos) |

## 🔄 Modos de Teste

### Static Load (Carga Estática)
Mantém um número constante de usuários durante toda a duração do teste.

```bash
python3 main.py --run static --users 50 --duration 120
```

### Ramp-up Load (Carga Progressiva)
Aumenta gradualmente o número de usuários ao longo do tempo.

```bash
python3 main.py --run ramp-up --users 100 --step-users 10 --interval-users 5 --duration 300
```

Neste exemplo:
- Inicia com 10 usuários
- A cada 5 segundos, adiciona mais 10 usuários
- Continua até atingir 100 usuários
- Mantém 100 usuários até completar 300 segundos

### Combinação de Parâmetros

#### Modo Paired (Pareado)
Combina os parâmetros na mesma posição das listas:

```bash
python3 main.py --type paired --users 10 50 100 --duration 60 120 180
```

Executa 3 testes:
- Teste 1: 10 usuários por 60s
- Teste 2: 50 usuários por 120s
- Teste 3: 100 usuários por 180s

#### Modo Cartesian (Produto Cartesiano)
Combina todos os valores possíveis:

```bash
python3 main.py --type cartesian --users 10 50 --duration 60 120
```

Executa 4 testes:
- 10 usuários por 60s
- 10 usuários por 120s
- 50 usuários por 60s
- 50 usuários por 120s

## 🔥 Warm-up

O warm-up é uma fase opcional que precede os testes principais, permitindo que o sistema "aqueça" antes das medições reais.

```bash
python3 main.py --warmup-duration 30 --warmup-users 5 --users 50 --duration 120
```

## 📊 Resultados (Outputs)

Os resultados são salvos automaticamente na pasta `results/<timestamp>/`.

### Estrutura de Diretórios

```
results/
└── DD-MM-YYYY_HH-MM-SS/{erc721/,erc1155/}
    ├── args_run.json              # Parâmetros da execução
    ├── api-tx-build/
    │   ├── out.csv                # Dados brutos
    |   ├── stats_global.csv           # Resumo global
    |   ├── stats_task.csv             # Estatísticas por tarefa
    |   ├── stats_endpoint.csv         # Estatísticas por endpoint
    |   └── stats_task_endpoint.csv    # Estatísticas por tarefa e endpoint
    ├── api-read-only/
    │   ├── out.csv
    |   ├── stats_global.csv           # Resumo global
    |   ├── stats_task.csv             # Estatísticas por tarefa
    |   ├── stats_endpoint.csv         # Estatísticas por endpoint
    |   └── stats_task_endpoint.csv    # Estatísticas por tarefa e endpoint
    ├── plot_latency.png           # Gráfico de latência
    ├── plot_throughput.png        # Gráfico de vazão (RPS)
    ├── plot_success_count.png     # Gráfico de requisições bem-sucedidas
    ├── plot_txbuild_stacked.png   # Gráfico empilhado de transações
    ├── plot_txbuild_grouped_log.png  # Gráfico detalhado (escala log)
    └── global_rps_comparison.png  # Comparação de RPS ao longo do tempo
```

### Arquivos CSV

#### `out.csv`
Log bruto de todas as operações (API e Blockchain) de cada usuário.

Colunas: `timestamp`, `user_id`, `task`, `endpoint`, `duration`, `status`, `error`

#### `stats_global.csv`
Resumo executivo contendo RPS global, total de requisições e contagem de users.

#### `stats_task.csv`
Estatísticas agrupadas por tipo de tarefa (ex: `TX-SEND`, `API-GET`).

Métricas: média, mediana, P50, P90, P99, desvio padrão, min, max, contagem

#### `stats_endpoint.csv`
Estatísticas por endpoint/função específica.

#### `stats_task_endpoint.csv`
Estatísticas por tarefa e endpoint.

### Gráficos Gerados

#### Gráficos Agregados (Comparação entre Testes)

1. **`plot_latency.png`**: Latência média vs. número de usuários (com intervalos de confiança 95%)
2. **`plot_throughput.png`**: Vazão (req/s) vs. número de usuários
3. **`plot_success_count.png`**: Total de requisições bem-sucedidas vs. número de usuários
4. **`plot_txbuild_stacked.png`**: Análise empilhada do tempo de construção de transações (API, Queue, Build, Sign, Send)
5. **`plot_txbuild_grouped_log.png`**: Detalhamento de latência por etapa em escala logarítmica
6. **`global_rps_comparison.png`**: Evolução do RPS ao longo do tempo para todos os testes

## 🎯 Exemplos de Uso

### Teste Rápido de Validação
```bash
python3 main.py --users 5 --duration 30 --contract erc721 --run static
```

### Teste de Escalabilidade
```bash
python3 main.py --type paired \
  --users 10 25 50 100 200 \
  --duration 120 180 240 300 360 \
  --run both --contract both
```

### Teste com Warm-up
```bash
python3 main.py --warmup-duration 60 --warmup-users 10 \
  --users 100 --duration 300 --run ramp-up \
  --step-users 10 --interval-users 10
```

### Teste Comparativo de Contratos
```bash
python3 main.py --contract both --users 50 --duration 120 --run static
```

## 📝 Notas Importantes

- **Carteiras**: Cada usuário virtual possui uma carteira Ethereum única gerada automaticamente
- **Concorrência**: Implementado usando `ThreadPoolExecutor` para simular usuários concorrentes
- **Logs**: Logs detalhados são salvos em `results/<timestamp>/load_testing.log`
- **Idempotência**: Cada execução cria um diretório timestamped único para evitar sobrescrita
