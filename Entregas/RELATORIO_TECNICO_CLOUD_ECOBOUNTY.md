# RELATÓRIO TÉCNICO: PROJETO FINAL - CLOUD COMPUTING & ESTRUTURAS DE DADOS AVANÇADAS

**Instituição:** UNIMA - AFYA  
**Curso:** Ciência da Computação / Engenharia de Software  
**Disciplina:** Cloud Computing & Estruturas de Dados  
**Projeto:** **EcoBounty — Plataforma Serverless em Nuvem e Logística Reversa Urbana**  
**Integrantes:**
- Mathias Borges
- Allan Gabriel
- Kauê Lucas  

---

## 1. Identificação do Projeto e Problema Real

### 1.1 O Problema
A cidade de Maceió (AL), a exemplo de diversas capitais litorâneas brasileiras, enfrenta desafios crônicos de descarte irregular de resíduos sólidos em encostas, praias e terrenos baldios, gerando pontos críticos de contaminação e vetores de doenças. Embora existam cooperativas homologadas de catadores (como a **COOPLUM** em Jacarecica) e ecopontos municipais distribuídos pela capital, há um abismo operacional e de incentivo:
1. A população carece de um canal imediato e confiável para denunciar focos de lixo com coordenadas georreferenciadas.
2. Catadores autônomos e cooperativas trabalham de forma desarticulada, sem garantia de remuneração direta pela limpeza de pontos críticos.
3. Não há mecanismos automatizados de auditoria que comprovem que uma área foi efetivamente limpa antes do desembolso de recompensas financeiras.

### 1.2 A Solução: EcoBounty
O **EcoBounty** é uma solução de impacto socioambiental (alinhada aos **ODS 11 — Cidades Sustentáveis** e **ODS 12 — Consumo e Produção Responsáveis** da ONU) baseada em uma arquitetura moderna de **Computação em Nuvem (Google Cloud Platform & Firebase for Students)** associada a **Estruturas de Dados e Algoritmos Avançados**.

A plataforma opera no modelo de *bounties* (recompensas ecológicas):
- **Cidadão:** Fotografa um ponto de descarte irregular em Maceió. A imagem é enviada para a nuvem (Firebase Cloud Storage), auditada por Visão Computacional (Google Cloud Vision API / Cloud Functions) e catalogada geograficamente no Cloud Firestore.
- **Coletor:** Acessa o aplicativo autenticado com Google Auth ou e-mail, visualiza as missões ordenadas algorítmicamente por valor ou proximidade, desloca-se até o local e executa a Fase 1 (limpeza).
- **Auditoria Serverless em Nuvem:** A foto da área limpa é processada por uma função Serverless (Google Cloud Functions); aprovada a limpeza, 50% da recompensa é adiantada na carteira digital e sincronizada no Cloud Firestore.
- **Roteamento por Grafos (Fase 2):** O algoritmo de Dijkstra calcula o trajeto viário ótimo até a cooperativa COOPLUM ou ecoponto mais próximo. O coletor entrega o material, comprova a entrega com foto do descarte e recebe os 50% restantes (validação 100% fotográfica).

---

## 2. Arquitetura da Solução em Nuvem (Google Cloud Platform & Firebase)

O projeto foi estruturado integralmente sobre o ecossistema **Google Cloud Platform & Firebase (Projeto `ecobounty-9d250`)**, aproveitando o plano gratuito (Firebase Spark e cotas educacionais Google for Students) com o princípio de **Custo Zero Real** com componentes *Serverless*.

### 2.1 Diagrama da Arquitetura em Nuvem

```
+-----------------------------------------------------------------------------------+
|                           CLIENT TIER (Flet / Web / Mobile)                       |
|   [Cidadão: Denúncia]               [Coletor: Limpeza]              [Admin / ESG] |
|                               [Google Auth Federado]                              |
+------------------------+--------------------------+-------------------------------+
                         |                          |
                    (HTTPS/REST)               (HTTPS/REST)
                         v                          v
+-----------------------------------------------------------------------------------+
|               GOOGLE CLOUD PLATFORM & FIREBASE (ecobounty-9d250)                  |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   | 1. INGESTÃO & ARMAZENAMENTO PERSISTENTE (R2)                              |   |
|   |    Firebase Cloud Storage: `ecobounty-9d250.firebasestorage.app`          |   |
|   |    - Fotos de denúncias cidadãs (JPEG georreferenciado)                   |   |
|   |    - Comprovação de limpeza (Phase 1 e Phase 2)                           |   |
|   |    - URLs seguras de download e acesso controlado                         |   |
|   +-------------------------------------+-------------------------------------+   |
|                                         | Event Trigger / Cloud REST              |
|                                         v                                         |
|   +---------------------------------------------------------------------------+   |
|   | 2. COMPUTAÇÃO SERVERLESS & PROCESSAMENTO (R3)                             |   |
|   |    Cloud Functions / Cloud Run: `ecobounty-audit-processor`               |   |
|   |    - Validação de integridade e metadados de auditoria                    |   |
|   |    - Liberação de adiantamento de 50% de bounty                           |   |
|   |    - Cálculos de complexidade assintótica e roteamento                    |   |
|   +-------------------+-----------------------------------+-------------------+   |
|                       |                                   |                       |
|                       v                                   v                       |
|   +-----------------------------------+   +-----------------------------------+   |
|   | 3. VISÃO COMPUTACIONAL (R5)       |   | 4. PERSISTÊNCIA NoSQL (R2)        |   |
|   |    Google Cloud Vision API        |   |    Google Cloud Firestore         |   |
|   |    - Detecção de resíduos sólidos |   |    Coleções:                          |   |
|   |    - Confirmação de área limpa    |   |    - `bounties` (missões ativas)      |   |
|   |    - Análise de rótulos ambientais|   |    - `users` (saldo e perfis)         |   |
|   +-----------------------------------+   |    - `transactions` (ledger financeiro)|  |
|                                           |    - `history` (trilha de auditoria)  |   |
|                                           +-----------------------------------+   |
|   +---------------------------------------------------------------------------+   |
|   | 5. GOVERNANÇA, SEGURANÇA & REGRAS DE ACESSO (R6)                          |   |
|   |    - Google Cloud IAM & Service Account Admin SDK                         |   |
|   |    - Firebase Security Rules (`firestore.rules` na raiz)                  |   |
|   |    - Firebase CLI Manifest (`firebase.json` na raiz)                      |   |
|   |    - Google Auth Identity Federation                                      |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
```

### 2.2 Modelos de Serviço Empregados
- **PaaS (Platform as a Service) / Serverless:** Google Cloud Functions, Cloud Run e Firebase Storage eliminam a sobrecarga de gerenciar sistemas operacionais e provisionar servidores, escalando sob demanda.
- **SaaS (Software as a Service):** Google Cloud Vision API provê modelos de aprendizado profundo (Deep Learning) consumidos via API REST de alta disponibilidade para validação de imagens.
- **BaaS (Backend as a Service):** Cloud Firestore e Firebase Auth gerenciam autenticação em tempo real, sincronização reativa e persistência NoSQL distribuída.

---

## 3. Mapeamento Formal dos Requisitos do Projeto UNIMA (R1 a R6)

| Requisito do PDF | Mapeamento no EcoBounty (Google Cloud / Firebase) | Evidência de Implementação |
|---|---|---|
| **R1 — Provedor de Nuvem** | Google Cloud Platform & Firebase for Students (`ecobounty-9d250`). Autenticação via Service Account JSON e Google Auth. | Módulos `app/cloud/gcp_provider.py`, `app/config.py` e Service Account oficial. |
| **R2 — Armazenamento em Nuvem** | **Firebase Cloud Storage** para fotos de auditoria e **Google Cloud Firestore** para documentos NoSQL (`bounties`, `users`, `transactions`, `history`). | Métodos `upload_image()`, `firestore_put_bounty()` e `app/services/firestore_service.py`. |
| **R3 — Processamento na Nuvem** | **Google Cloud Functions / Cloud Run** (`ecobounty-audit-processor`). Execução serverless de regras de negócio, cálculo de adiantamento (50%) e auditoria anti-fraude. | Função `cloud_function_audit_handler()` em Python 3.11 com testes automatizados em `tests/test_gcp_cloud.py`. |
| **R4 — Aplicação Funcional** | Interface completa Flet (Web, Desktop, Celular) e API REST estruturada com validação de entrada, processamento e feedback reativo. | Interface visual com `LoginView` (Google Auth), `CameraView`, `HomeView`, `RouteView`, `RewardView`. |
| **R5 — Integração dos Serviços** | Pipeline integrado ponta a ponta: Foto enviada ao Firebase Storage $\rightarrow$ Cloud Function processa $\rightarrow$ Cloud Vision valida $\rightarrow$ Cloud Firestore persiste $\rightarrow$ Flet UI atualiza em tempo real. | Fluxo completo verificado em `tests/test_gcp_cloud.py` e no script `demo_algoritmos_nuvem.py`. |
| **R6 — Segurança e Custos** | Zero credenciais no código-fonte (.env e Service Account externa); Firebase Security Rules granulares (`firestore.rules`); Custo R$ 0,00 coberto integralmente pelo plano gratuito / estudante. | Arquivos `firestore.rules` e `firebase.json` na raiz e documentação de segurança. |

---

## 4. Integração das Estruturas de Dados (1ª Unidade)

O EcoBounty implementa estruturas de dados clássicas de forma customizada e tipada em `app/data_structures/`:

1. **Vetor Dinâmico (`CustomVector`):**
   - *Funcionamento:* Alocação sequencial com fator de crescimento geométrico ($2\times$) e acesso indexado $O(1)$.
   - *Aplicação:* Catálogo em memória para renderização fluida das listas de bounties na tela inicial.
2. **Listas Encadeadas (`LinkedList` e `DoublyLinkedList`):**
   - *Funcionamento:* Nós contendo referências `next` e `prev`, permitindo inserções e exclusões em $O(1)$ sem necessidade de realocação de blocos contíguos.
   - *Aplicação:* Trilha cronológica de auditoria de cada missão (check-in, upload da foto, aprovação da IA, check-out no ecoponto) e estrutura de buckets para colisão de hash.
3. **Lista Linear Restrita (`RestrictedLinearList`):**
   - *Funcionamento:* Lista sequencial com limite rígido de capacidade máxima (*Bounded Array*) e tratamento estrito de overflow e underflow.
   - *Aplicação:* Gerenciamento dos slots de missões ativas concorrentes do coletor (limite regulamentar de no máximo 5 missões em andamento simultâneo para coibir monopolização de chamados).
4. **Pilha (`Stack` e `UndoRedoManager`):**
   - *Funcionamento:* Política LIFO (*Last-In, First-Out*) com métodos `push()`, `pop()` e `peek()`.
   - *Aplicação:* Sistema de Desfazer/Refazer (*Undo/Redo*) para reversão imediata de aceite acidental de missões pelo coletor, retornando o status do bounty para DISPONÍVEL no banco.
5. **Fila (`Queue`):**
   - *Funcionamento:* Política FIFO (*First-In, First-Out*) com métodos `enqueue()` e `dequeue()`.
   - *Aplicação:* Fila de upload e despacho assíncrono de fotos de denúncias para o Firebase Cloud Storage e Cloud Functions na ordem de recebimento.
6. **Deque (`Deque`):**
   - *Funcionamento:* Fila duplamente terminada com inserções e remoções eficientes nas duas extremidades (`append_left` / `append_right`).
   - *Aplicação:* Fila de auditoria prioritária onde denúncias de alto risco ambiental (ex: contaminação de mananciais) furam a fila pela esquerda em $O(1)$.

---

## 5. Diferenciais Obrigatórios da 2ª Unidade

### 5.1 Diferencial 1: Tabelas Hash e Justificativa de Software

Foram implementadas duas classes completas em `app/data_structures/hash_table.py`:
- `SeparateChainingHashTable`: Tratamento de colisão por encadeamento separado.
- `OpenAddressingHashTable`: Tratamento de colisão por endereçamento aberto, com suporte a **Sondagem Linear** e **Hash Duplo**.
- Funções de dispersão: Método da Divisão ($h(k) = k \bmod m$), Método da Multiplicação de Knuth ($h(k) = \lfloor m \cdot (k \cdot A \bmod 1) \rfloor$, $A \approx 0.618033$) e Polinomial djb2 para chaves em string.

#### Justificativa Técnica para a Apresentação:
- **Por que usamos Encadeamento Separado no Catálogo de Bounties?**  
  O fluxo de denúncias comunitárias é altamente volátil e imprevisível. Novas denúncias entram constantemente e saem do catálogo assim que concluídas. O encadeamento separado não sofre com agrupamento (*clustering*) primário ou secundário e tolera temporariamente fatores de carga $\alpha > 1.0$ sem risco de interrupção ou recusa de inserção, garantindo estabilidade ao aplicativo.
- **Por que usamos Endereçamento Aberto (Hash Duplo) no Cache de Sessão e Ecopontos?**  
  O número de ecopontos em Maceió e de sessões de coletores é delimitado e de alta frequência de leitura por segundo. O endereçamento aberto mantém todos os pares chave-valor em um array contíguo na memória principal, aproveitando a localidade espacial das linhas de cache L1/L2 do processador. O Hash Duplo ($h(k, i) = (h_1(k) + i \cdot h_2(k)) \bmod m$) elimina totalmente o agrupamento primário e secundário com latência estrita $O(1)$.

---

### 5.2 Diferencial 2: Algoritmos de Grafos (Geolocalização) & Visualização Matplotlib

A malha urbana de Maceió foi modelada em `app/algorithms/graphs.py` através da classe `MaceioEcoGraph`, integrando 12 nós estratégicos (Ecopontos de Pajuçara, Ponta Verde, Jatiúca, Cruz das Almas, Mangabeiras, Centro, Farol, Trapiche, Tabuleiro, Benedito Bentes e a Cooperativa **COOPLUM** em Jacarecica), interligados por arestas ponderadas com distâncias reais (km).

#### Algoritmo de Menor Caminho (Dijkstra):
Calcula a rota viária ótima desde o local da coleta até a destinação final.  
Exemplo executado: Coleta no **Ecoponto Trapiche da Barra** com destino à **Cooperativa COOPLUM**:
$$\text{Rota Ótima: } \text{Trapiche} \xrightarrow{3.1\text{km}} \text{Centro} \xrightarrow{2.2\text{km}} \text{Farol} \xrightarrow{4.5\text{km}} \text{Cruz das Almas} \xrightarrow{2.3\text{km}} \text{COOPLUM} \quad (\text{Total: } 12.1\text{ km})$$

#### Exibição Gráfica via Matplotlib:
O módulo `app/algorithms/visualizer.py` renderiza o grafo geográfico com coordenadas precisas de latitude/longitude, destacando a rota ótima de Dijkstra em verde esmeralda neon (`#10b981`), nós de origem em ciano brilhante (`#38bdf8`) e cooperativa de destino em verde (`#22c55e`), com anotações de distância por trecho.
- Imagem gerada: `Entregas/grafo_maceio_rotas.png` e `app/assets/grafo_maceio_rotas.png`.

---

### 5.3 Diferencial 3: Algoritmos de Ordenação & Comparativo Gráfico de Desempenho

Em `app/algorithms/sorting.py`, foram implementados os quatro métodos clássicos:
1. **Método da Bolha (Bubble Sort)** — Complexidade $O(N^2)$
2. **Inserção Direta (Insertion Sort)** — Complexidade $O(N^2)$ pior/médio, $O(N)$ melhor
3. **Seleção Direta (Selection Sort)** — Complexidade $O(N^2)$ fixo
4. **QuickSort com Partição Mediana de 3** — Complexidade $O(N \log N)$ médio

#### Aplicação no EcoBounty:
- Ordenação de missões por maior recompensa financeira (`sort_bounties_by_reward`).
- Ordenação por menor distância geodésica ao coletor via Haversine (`sort_bounties_by_distance`).
- Ordenação por urgência e carimbo de data (`sort_bounties_by_urgency`).

#### Resultados do Benchmark Comparativo ($N = 1000$ elementos reais):
| Algoritmo | Tempo Médio (ms) | Comparações | Trocas / Deslocamentos |
|---|---|---|---|
| **Bubble Sort** | 142.74 ms | 495.759 | 248.144 |
| **Insertion Sort** | 50.03 ms | 249.140 | 248.144 |
| **Selection Sort** | 113.43 ms | 499.500 | 994 |
| **QuickSort (Otimizado)** | **3.27 ms** | **9.191** | **6.153** |

*Análise:* O **QuickSort** foi mais de **43 vezes mais rápido** que o Bubble Sort para $N=1000$, comprovando sua superioridade assintótica $O(N \log N)$ para o ordenamento dinâmico de milhares de chamados ambientais.
- Gráficos comparativos gerados com Matplotlib: `Entregas/benchmark_ordenacao.png` e `app/assets/benchmark_ordenacao.png`.

---

## 6. Segurança, Consumo e Estimativa de Custos na Nuvem

### 6.1 Segurança da Informação
- **Proteção de Segredos:** Nenhuma credencial, senha ou chave de API está presente no código-fonte. O carregamento é feito através de variáveis de ambiente do sistema operacional ou arquivo `.env`.
- **Firebase Security Rules:** Arquivo operacional `firestore.rules` posicionado na raiz do repositório, garantindo controle estrito de leitura/escrita e imutabilidade de transações financeiras.
- **Autenticação Federada Google Auth:** Permite login sem senha gerenciada localmente, reduzindo a superfície de ataque.

### 6.2 Estimativa de Custos (Google Cloud Free Tier / Firebase Spark)
O dimensionamento do EcoBounty foi projetado para operar com **Custo R$ 0,00**:
1. **Firebase Cloud Storage:** Até 5 GB de armazenamento e 1 GB/dia de download gratuitos.
2. **Cloud Functions:** 2.000.000 de invocações gratuitas por mês.
3. **Cloud Firestore:** 1 GB de armazenamento NoSQL, 50.000 leituras/dia e 20.000 escritas/dia gratuitas.
4. **Google Cloud Vision API:** 1.000 requisições mensais gratuitas de detecção de rótulos.
5. **Google for Students:** O saldo em créditos de estudante permanece 100% preservado.

---

## 7. Evidências de Testes e Validação Automatizada

O projeto conta com uma suíte abrangente de **103 testes automatizados** aprovados com 100% de sucesso via `pytest`:
- `tests/test_data_structures.py`: 13 testes cobrindo Vetor (indexação negativa O(1)), Listas Encadeadas, Lista Linear Restrita, Pilha, Fila e Deque.
- `tests/test_hash_tables.py`: 10 testes cobrindo Encadeamento Separado, Endereçamento Aberto (Linear e Duplo com coprimilidade garantida por capacidade prima e tombstones).
- `tests/test_graphs.py`: 5 testes cobrindo o Grafo de Maceió, Dijkstra, BFS e DFS.
- `tests/test_sorting_algorithms.py`: 11 testes cobrindo os 4 algoritmos, casos extremos, mitigação de estouro de recursão e benchmark.
- `tests/test_gcp_cloud.py`: 7 testes cobrindo Firebase Storage, Cloud Firestore, Cloud Functions, Cloud Vision, Google Auth, regras e geração de artefatos.
- `tests/test_firestore.py`: 4 testes cobrindo operações completas CRUD de Firestore em modo real e simulado.
- `tests/test_auth.py`, `tests/test_bounties.py`, `tests/test_camera_auth_adaptive.py`, `tests/test_views.py`, `tests/test_wallet.py`: 53 testes cobrindo os fluxos funcionais da aplicação.

---

## 8. Conclusão

O projeto **EcoBounty** uniu com rigor os conceitos de **Estruturas de Dados** (1ª e 2ª Unidades) e de **Computação em Nuvem (Google Cloud & Firebase)** para criar uma solução de engenharia de software robusta, escalável e de alto impacto social para a cidade de Maceió. A arquitetura serverless no Google Cloud viabiliza um sistema gratuito, auditável e resiliente para o ecossistema de reciclagem e limpeza urbana.
