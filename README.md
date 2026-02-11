# SmartAgroRAF Load Testing Tool

Este repositório contém uma ferramenta de teste de carga personalizada para avaliar o desempenho da plataforma SmartAgroRAF, focando em interações com Blockchain (Besu) e API.

## Estrutura do Projeto

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
    *   Gerencia tarefas assíncronas (`asyncio`) e requisições HTTP (`aiohttp`) para simular usuários concorrentes de forma eficiente.
    *   Controla os modos de teste: **Static** (carga constante) e **Ramp-up** (aumento gradual de usuários).
    *   Coleta os resultados brutos de cada "usuário".

*   **`users/`**:  
    Define o comportamento dos usuários virtuais.
    *   `User`: Classe base que contém a lógica de "campanhas" (sequências de ações).
    *   `UserERC721` / `UserERC1155`: Especializações para diferentes tipos de contrato.
    *   Cada usuário possui sua própria carteira (`Wallet`) e contadores de métricas.

*   **`tasks/`**:  
    Camada de execução de baixo nível.
    *   `TaskAPI`: Realiza chamadas HTTP assíncronas de alta performance utilizando `aiohttp`.
    *   `TaskBlockchain`: Constrói, assina e envia transações para a rede blockchain usando `web3.py`.

*   **`save.py`**:  
    Responsável pela persistência de dados.
    *   `save_all_outputs`: Função central que salva os resultados brutos, resumo global e estatísticas detalhadas.

*   **`stats.py`**:  
    Módulo de cálculo estatístico.
    *   A classe `Stats` processa os CSVs brutos para calcular média, mediana, percentis (P50, P90, P99) e RPS (Requests Per Second).

*   **`plot/`**:  
    Módulo de geração de gráficos e visualizações.
    *   **`plot.py`**: Orquestrador principal que chama todas as funções de plotagem.
    *   **`common.py`**: Funções utilitárias compartilhadas, constantes de estilo e formatação.
    *   **`plot_latency.py`**: Gráfico comparativo de latência entre contratos.
    *   **`plot_throughput.py`**: Gráfico de vazão (RPS) comparativo.
    *   **`plot_success_count.py`**: Gráfico de contagem de requisições bem-sucedidas.
    *   **`plot_success_fail.py`**: Gráficos de comparação sucesso vs. falha por fase.
    *   **`plot_txbuild_stacked.py`**: Análise empilhada de componentes de transação.
    *   **`plot_txbuild_grouped.py`**: Análise agrupada de componentes de transação (linear e log).
    *   **`plot_read_routes.py`**: Análise detalhada de rotas de leitura por contrato.
    *   **`plot_tx_build_routes.py`**: Análise detalhada de rotas de escrita por contrato.
    *   **`plot_read_latency.py`**: Latência individual e consolidada de rotas de leitura.
    *   **`plot_tx_build_latency.py`**: Latência individual e consolidada de rotas de escrita.
    *   **`plot_rps_comparison.py`**: Evolução temporal do RPS.
    *   Gera automaticamente visualizações em PNG e PDF para análise detalhada.

*   **`config.py`**:  
    Variáveis de ambiente, URLs da API/RPC e configurações globais.

## Pré-requisitos e Configuração

### Ambiente Virtual Python (venv)

É **altamente recomendado** usar um ambiente virtual Python para isolar as dependências do projeto. Siga os passos abaixo:

#### 1. Criar o ambiente virtual

```bash
python3 -m venv venv
```

#### 2. Ativar o ambiente virtual

```bash
source venv/bin/activate
```

#### 3. Instalar as dependências

Com o ambiente virtual ativado, instale as bibliotecas necessárias:

```bash
pip install -r requirements.txt
```

#### 4. Desativar o ambiente virtual (quando terminar)

```bash
deactivate
```

> **Nota**: Sempre ative o ambiente virtual antes de executar os testes ou scripts de plotagem.

## Como Executar

O script é executado via linha de comando. Exemplo básico:

```bash
python3 main.py --users 10 --duration 60 --run static --contract erc721
```

## Parâmetros Disponíveis

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
| `--duration` | float[] | [10.0] | Duração do teste em segundos (aceita múltiplos valores) |
| `--users` | int[] | [10] | Número de usuários simultâneos (aceita múltiplos valores) |
| `--step-users` | int[] | [1] | Número de usuários adicionados a cada incremento (modo ramp-up) |
| `--interval-users` | float[] | [1.0] | Tempo entre incrementos de usuários em segundos (modo ramp-up) |
| `--interval-requests` | float | 1.0 | Pausa entre requisições consecutivas do mesmo usuário (em segundos) |

### Parâmetros de Warm-up

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `--warmup-users` | int | 10 | Número de usuários no warm-up |
| `--warmup-duration` | float | 10 | Duração do warm-up em segundos (0 = desabilitado) |
| `--warmup-step-users` | int | 1 | Incremento de usuários no warm-up |
| `--warmup-interval-users` | float | 1.0 | Tempo entre incrementos no warm-up (segundos) |
| `--warmup-interval-requests` | float | 1.0 | Pausa entre requisições no warm-up (segundos) |

## Modos de Teste

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

## Warm-up

O warm-up é uma fase opcional que precede os testes principais, permitindo que o sistema "aqueça" antes das medições reais.

```bash
python3 main.py --warmup-duration 30 --warmup-users 5 --users 50 --duration 120
```

## Repetições de Teste

A ferramenta suporta execução de múltiplas repetições de cada configuração de teste para garantir resultados estatisticamente significativos.

```bash
python3 main.py --users 50 --duration 120 --repeat 3
```

### Como Funciona

1. **Execução**: Cada configuração é executada N vezes (definido por `--repeat`)
2. **Armazenamento**: Cada repetição gera um arquivo `out_rep-X.csv` separado
3. **Consolidação**: Após todas as repetições, as estatísticas são consolidadas automaticamente
4. **Análise**: Os gráficos utilizam médias e desvios padrão entre repetições para intervalos de confiança

### Benefícios

- **Confiabilidade**: Reduz o impacto de variações aleatórias
- **Intervalos de Confiança**: Permite calcular IC de 95% nos gráficos de latência
- **Detecção de Anomalias**: Facilita identificação de comportamentos inconsistentes

## Resultados (Outputs)

Os resultados são salvos automaticamente na pasta `results/<timestamp>/`.

### Estrutura de Diretórios

```
results/
└── DD-MM-YYYY_HH-MM-SS/{erc721/,erc1155/}
    ├── args_run.json              # Parâmetros da execução
    ├── api-tx-build/
    │   ├── out_rep-1.csv          # Dados brutos da repetição 1
    │   ├── out_rep-2.csv          # Dados brutos da repetição 2
    │   ├── out_rep-N.csv          # Dados brutos da repetição N
    │   ├── stats_global.csv       # Resumo global consolidado
    │   ├── stats_task.csv         # Estatísticas por tarefa
    │   ├── stats_endpoint.csv     # Estatísticas por endpoint
    │   └── stats_task_endpoint.csv # Estatísticas por tarefa e endpoint
    ├── api-read-only/
    │   ├── out_rep-1.csv          # Dados brutos da repetição 1
    │   ├── out_rep-2.csv          # Dados brutos da repetição 2
    │   ├── out_rep-N.csv          # Dados brutos da repetição N
    │   ├── stats_global.csv       # Resumo global consolidado
    │   ├── stats_task.csv         # Estatísticas por tarefa
    │   ├── stats_endpoint.csv     # Estatísticas por endpoint
    │   └── stats_task_endpoint.csv # Estatísticas por tarefa e endpoint
    └── plots/
        ├── png/                   # Gráficos em formato PNG
        │   ├── plot_latency.png
        │   ├── plot_throughput.png
        │   ├── plot_success_count.png
        │   ├── plot_txbuild_stacked.png
        │   ├── plot_txbuild_grouped.png
        │   ├── plot_txbuild_grouped_log.png
        │   ├── plot_success_fail_api-read-only.png
        │   ├── plot_success_fail_api-tx-build.png
        │   ├── plot_read_routes_erc721.png
        │   ├── plot_read_routes_erc1155.png
        │   ├── plot_tx_build_routes_erc721.png
        │   ├── plot_tx_build_routes_erc1155.png
        │   ├── plot_read_latency_*.png
        │   ├── plot_tx_build_latency_*.png
        │   └── global_rps_comparison.png
        └── pdf/                   # Gráficos em formato PDF
            ├── plot_latency.pdf
            ├── plot_throughput.pdf
            └── ... (mesmos arquivos em PDF)
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

A ferramenta gera automaticamente uma ampla variedade de gráficos para análise detalhada do desempenho. Todos os gráficos são salvos em formato PNG e PDF dentro do diretório `plots/`.

#### Gráficos Agregados (Comparação entre Contratos)

1. **`plot_latency.png`**: Latência média vs. número de usuários
   - Compara ERC-721 e ERC-1155
   - Inclui intervalos de confiança de 95%
   - Eixo Y fixo de 0-9 segundos para facilitar comparação

2. **`plot_throughput.png`**: Vazão (req/s) vs. número de usuários
   - Mostra requisições bem-sucedidas por segundo
   - Comparação entre contratos e tipos de experimento
   - Eixo Y de 0-1000 req/s

3. **`plot_success_count.png`**: Total de requisições bem-sucedidas vs. número de usuários
   - Visualiza a quantidade absoluta de requisições processadas com sucesso

#### Análise de Transações Blockchain

4. **`plot_txbuild_stacked.png`**: Análise empilhada do tempo de construção de transações
   - Decompõe o tempo total em: API, Queue, Build, Sign, Send
   - Visualização empilhada para entender a composição da latência

5. **`plot_txbuild_grouped.png`**: Detalhamento de latência por etapa (escala linear)
   - Barras agrupadas lado a lado para comparação direta
   - Separa ERC-721 e ERC-1155
   - Mostra todas as etapas: API-TX-BUILD, QUEUE, TX-BUILD, TX-SIGN, TX-SEND

6. **`plot_txbuild_grouped_log.png`**: Detalhamento de latência por etapa (escala logarítmica)
   - Mesma informação que o anterior, mas em escala log
   - Útil para visualizar diferenças em ordens de magnitude

#### Análise de Rotas Individuais

7. **Rotas de Leitura (Read Routes)**:
   - **`plot_success_fail_api-read-only.png`**: Comparação de requisições bem-sucedidas vs. falhas
   - **`plot_read_routes_erc721.png`**: Quantidade de requisições por rota (ERC-721)
   - **`plot_read_routes_erc1155.png`**: Quantidade de requisições por rota (ERC-1155)
   - **`plot_read_latency_erc721_all.png`**: Latência consolidada de todas as rotas de leitura (ERC-721)
   - **`plot_read_latency_erc1155_all.png`**: Latência consolidada de todas as rotas de leitura (ERC-1155)
   - **`plot_read_latency_all.png`**: Comparação lado a lado ERC-721 vs ERC-1155
   - **`plot_read_latency_route_*.png`**: Gráficos individuais para cada endpoint de leitura

8. **Rotas de Escrita (Write Routes - TX-Build)**:
   - **`plot_success_fail_api-tx-build.png`**: Comparação de requisições bem-sucedidas vs. falhas
   - **`plot_tx_build_routes_erc721.png`**: Quantidade de requisições por rota (ERC-721)
   - **`plot_tx_build_routes_erc1155.png`**: Quantidade de requisições por rota (ERC-1155)
   - **`plot_tx_build_latency_erc721_all.png`**: Latência consolidada de todas as rotas de escrita (ERC-721)
   - **`plot_tx_build_latency_erc1155_all.png`**: Latência consolidada de todas as rotas de escrita (ERC-1155)
   - **`plot_tx_build_latency_all.png`**: Comparação lado a lado ERC-721 vs ERC-1155
   - **`plot_tx_build_latency_route_*.png`**: Gráficos individuais para cada endpoint de escrita

#### Análise Temporal

9. **`global_rps_comparison.png`**: Evolução do RPS ao longo do tempo
   - Mostra como a vazão varia durante a execução do teste
   - Útil para identificar padrões de degradação ou estabilização

## Gerando Gráficos de Resultados Existentes

Você pode gerar ou regenerar gráficos a partir de resultados já coletados sem executar novos testes:

```bash
python3 main.py --plot results/04-02-2026_12-30-45
```

### Reconsolidação Automática de Estatísticas

Quando você usa o parâmetro `--plot`, a ferramenta automaticamente:

1. **Escaneia** todos os diretórios de teste no caminho fornecido
2. **Detecta** arquivos `out_rep-*.csv` em cada fase (api-tx-build, api-read-only)
3. **Reconsolida** as estatísticas a partir dos dados brutos
4. **Gera** os arquivos `stats_*.csv` atualizados
5. **Cria** todos os gráficos com os dados consolidados

Isso é útil para:
- **Regenerar estatísticas** após modificações no código de consolidação
- **Criar visualizações** de testes antigos sem re-executar
- **Experimentar** diferentes formatos ou escalas de gráficos
- **Corrigir** estatísticas sem precisar refazer os testes completos

## Exemplos de Uso

### Teste Rápido de Validação
```bash
python3 main.py --users 5 --duration 30 --contract erc721 --run static
```

### Teste de Escalabilidade Completo
```bash
python3 main.py --type paired \
  --users 10 25 50 100 200 \
  --duration 120 180 240 300 360 \
  --run both --contract both \
  --repeat 3
```

### Teste com Warm-up e Repetições
```bash
python3 main.py --warmup-duration 60 --warmup-users 10 \
  --users 100 --duration 300 --run ramp-up \
  --step-users 10 --interval-users 10 \
  --repeat 5
```

### Teste Comparativo de Contratos
```bash
python3 main.py --contract both --users 50 --duration 120 --run static --repeat 3
```

### Teste de Carga Progressiva Detalhado
```bash
python3 main.py --run ramp-up \
  --users 200 --step-users 20 --interval-users 10 \
  --duration 600 --interval-requests 0.5 \
  --repeat 3
```

### Regenerar Estatísticas e Gráficos de Teste Anterior
```bash
# Reconsolida estatísticas dos arquivos out_rep-*.csv e regenera todos os gráficos
python3 main.py --plot results/04-02-2026_15-30-00
```

## Notas Importantes

### Arquitetura e Implementação

- **Carteiras**: Cada usuário virtual possui uma carteira Ethereum única gerada automaticamente
- **Concorrência Assíncrona**: Implementado usando `asyncio` e `aiohttp` para máxima eficiência
  - Requisições HTTP assíncronas via `aiohttp`
  - Interações blockchain assíncronas via `web3.py` async
  - Pool de conexões TCP otimizado para alto throughput
- **Logs Detalhados**: Logs completos são salvos em `results/<timestamp>/load_testing.log`
- **Idempotência**: Cada execução cria um diretório timestamped único para evitar sobrescrita

### Análise Estatística

- **Métricas Calculadas**: Média, mediana, P50, P90, P99, desvio padrão, min, max
- **RPS (Requests Per Second)**: Calculado automaticamente para cada fase
- **Intervalos de Confiança**: IC de 95% baseado em múltiplas repetições
- **Consolidação Automática**: Estatísticas agregadas de todas as repetições

### Visualizações

- **Formatos Múltiplos**: Todos os gráficos são salvos em PNG (alta resolução) e PDF (vetorial)
- **Análise Granular**: Gráficos individuais para cada endpoint além de visões consolidadas
- **Comparações Diretas**: Visualizações lado a lado de ERC-721 vs ERC-1155
- **Escalas Adaptativas**: Suporte para escalas linear e logarítmica conforme necessário
- **Geração Sob Demanda**: Use `--plot <diretório>` para regenerar gráficos de resultados existentes

### Modos de Teste

- **API-Blockchain**: Modo completo que testa tanto leitura quanto escrita
- **Warm-up Configurável**: Fase opcional de aquecimento antes dos testes principais
- **Repetições Automáticas**: Suporte nativo para múltiplas execuções com consolidação estatística
