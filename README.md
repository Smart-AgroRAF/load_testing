# SmartAgroRAF Load Testing Tool

Este repositório contém uma ferramenta de teste de carga personalizada para avaliar o desempenho da plataforma SmartAgroRAF, focando em interações com Blockchain (Besu) e API off-chain.

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

*   **`config.py`**:  
    Variáveis de ambiente, URLs da API/RPC e configurações globais.

## 🚀 Como Executar

O script é executado via linha de comando. Exemplo básico:

```bash
python3 main.py --users 10 --duration 60 --type static --contract erc721
```

### Argumentos Principais
- `--users`: Número de usuários simultâneos (workers).
- `--duration`: Duração do teste em segundos.
- `--type`: Tipo de carga (`static` ou `ramp-up`).
- `--contract`: Tipo de contrato alvo (`erc721`, `erc1155`, etc.).
- `--mode`: Define o cenário de teste (ex: `write` para transações, `read` para consultas).

## 📊 Resultados (Outputs)

Os resultados são salvos automaticamente na pasta `results/<timestamp>/`.

*   **`out.csv`**: Log bruto de todas as operações (API e Blockchain) de cada usuário.
*   **`stats_global.csv`**: Resumo executivo contendo RPS global, total de requisições e contagem de workers.
*   **`stats_task.csv`**: Estatísticas agrupadas por tipo de tarefa (ex: `TX-SEND`, `API-GET`).
*   **`stats_endpoint.csv`**: Estatísticas por endpoint/função específica.
