# RELATÓRIO TÉCNICO OFICIAL: PROJETO FINAL — CLOUD COMPUTING & ESTRUTURAS DE DADOS AVANÇADAS

**Instituição:** Centro Universitário UNIMA — Afya (Maceió - AL)  
**Curso:** Engenharia de Software / Ciência da Computação  
**Disciplina:** Computação em Nuvem (Cloud Computing) & Estruturas de Dados  
**Título do Projeto:** **EcoBounty — Economia Circular Gamificada e Plataforma em Nuvem para Logística Reversa Urbana**  

**Integrantes do Grupo:**
- **Allan Gabriel de Holanda Paz** — Engenharia de Software / Arquitetura em Nuvem e Integração
- **Kaue Lucas Barbosa Silva** — Engenharia de Software / Algoritmos, Estruturas de Dados e Backend
- **Mathias Borges Marques** — Engenharia de Software / Serviços Cloud, Banco NoSQL e Testes

**Links Oficiais dos Entregáveis:**
- **Aplicação Funcional em Nuvem (Render PaaS):** [https://ecobounty-app.onrender.com](https://ecobounty-app.onrender.com)
- **Repositório Público Oficial no GitHub (Entregável B — Sem Credenciais):** [https://github.com/MathiasBorges/ecobounty-cloud](https://github.com/MathiasBorges/ecobounty-cloud)

---

## 1. Identificação do Grupo e Título do Projeto

O projeto **EcoBounty** consiste no desenvolvimento, configuração e disponibilização de uma plataforma distribuída em nuvem voltada à resolução do descarte irregular de resíduos sólidos urbanos em Maceió (AL), integrando hospedagem **PaaS (Render)**, banco de dados NoSQL em tempo real **BaaS/DBaaS (Google Cloud Firestore)**, autenticação federada **Google Auth (Firebase Authentication)**, armazenamento de objetos em **CDN (Catbox / Firebase Storage)** e processamento de Visão Computacional Multimodal **SaaS (Google Gemini API)**.

---

## 2. Problema e Objetivo da Solução

### 2.1 O Problema Real Enfrentado
A cidade de Maceió (AL), marcada geograficamente por tabuleiros, vales e encostas litorâneas (*grotas*), enfrenta desafios crônicos de descarte irregular de resíduos sólidos em encostas (como Farol, Jacintinho e Grota do Cigano), terrenos baldios e faixas litorâneas. Embora existam cooperativas homologadas de catadores (com destaque para a **COOPLUM** em Jacarecica) e ecopontos municipais mantidos pela ALURB, há três gargalos operacionais críticos:
1. **Desarticulação entre Cidadãos e Coleta:** Ausência de um canal ágil e georreferenciado para reportar pontos críticos de lixo com fotos e coordenadas exatas de GPS.
2. **Falta de Incentivo Financeiro Direto ao Coletor:** Catadores autônomos realizam a remoção braçal sem garantia de remuneração imediata proporcional ao esforço de desobstrução.
3. **Insegurança na Auditoria para Patrocinadores ESG:** Empresas com metas ambientais e órgãos públicos careciam de auditoria automatizada que comprovasse a limpeza efetiva do local antes da liberação de recompensas financeiras.

### 2.2 Objetivo da Aplicação
Projetar, implementar e operar na Internet uma aplicação funcional de Computação em Nuvem alinhada aos **ODS 11 (Cidades e Comunidades Sustentáveis)** e **ODS 12 (Consumo e Produção Responsáveis)** da ONU, capaz de:
1. Permitir o registro de denúncias georreferenciadas por cidadãos via navegador Web ou aplicativo Mobile Android (TWA/APK);
2. Auditar de forma 100% automatizada na nuvem o *antes e depois* da área limpa utilizando Visão Computacional Multimodal (**Google Gemini API**);
3. Remunerar o coletor em duas fases auditáveis (**50% de adiantamento** após limpeza do terreno e **50% finais** após entrega homologada em cooperativa/ecoponto);
4. Calcular a rota viária de menor custo em quilômetros até a cooperativa **COOPLUM** ou ecoponto mais próximo por meio do **Algoritmo de Dijkstra** e roteamento OSRM/OpenStreetMap HD;
5. Operar com **Custo Zero Real (`R$ 0,00`)** sobre planos gratuitos de nuvem.

---

## 3. Descrição das Funcionalidades da Aplicação

1. **Módulo Cidadão (Registro de Denúncias em Nuvem):** Captura fotográfica *in-page* via câmera ou galeria com extração automática de latitude e longitude via GPS. A imagem é persistida na nuvem (Catbox CDN), classificada pela IA (plásticos, metais, papelão, vidro, entulho) e sincronizada na coleção `bounties` do Google Cloud Firestore com status `DISPONIVEL`.
2. **Módulo Coletor (Filtros Algorítmicos, Travas de Capacidade e Undo/Redo):** Visualização de missões ordenadas via **QuickSort com Mediana de Três** por recompensa (`R$`), distância geodésica (Haversine) ou urgência. Conta com limite concorrencial rígido de no máximo **5 missões simultâneas** via `RestrictedLinearList` e reversão imediata de aceite acidental em $O(1)$ via Pilha LIFO (`UndoRedoManager`).
3. **Ciclo de Missão em 2 Fases (Regra 50/50):**
   - **Fase 1 (Limpeza do Terreno):** O coletor envia a foto do local limpo; a API do Gemini compara o *antes e depois* e, se aprovada, libera 50% de adiantamento na carteira digital (`FASE1_CONCLUIDA`).
   - **Fase 2 (Destinação Homologada):** O app traça a rota ótima de Dijkstra até o ecoponto/COOPLUM; comprovado o descarte, quita os 50% restantes (`ENTREGUE`).
4. **Carteira Digital e Livro-Razão Contábil (*Ledger* Idempotente):** Registro imutável na coleção `transactions` do Firestore protegido por chaves únicas de idempotência (`advance_{user_id}_{bounty_id}` e `completion_{user_id}_{bounty_id}`).

| Status da Missão | Ação do Usuário | Processamento na Nuvem | Efeito Financeiro |
| :---: | :--- | :--- | :--- |
| **`DISPONIVEL`** | Cidadão abre denúncia com foto | Upload na Catbox CDN e gravação NoSQL no Firestore | Reserva do valor no fundo |
| **`EM_ANDAMENTO`** | Coletor aceita o chamado no app | Trava atômica no Firestore; slot na `RestrictedLinearList` | Sem desembolso imediato |
| **`FASE1_CONCLUIDA`** | Coletor envia foto da área limpa | Auditoria Multimodal Gemini compara antes/depois | Crédito de 50% (Adiantamento) |
| **`ENTREGUE`** | Entrega na COOPLUM / Ecoponto | Validação fotográfica/QR Code de destinação correta | Crédito de 50% (Quitação Final) |

---

## 4. Arquitetura da Aplicação e Diagrama da Solução

```
+-----------------------------------------------------------------------------------+
|                    CAMADA DE APRESENTAÇÃO (Web / Mobile APK TWA)                  |
|   [Cidadão: Denúncia]        [Coletor: Limpeza & Rota]        [Mapa Leaflet HD]   |
|                        [Firebase Authentication / Google Auth]                    |
+------------------------+--------------------------+-------------------------------+
                         |                          |
                    (WSS / HTTPS)              (REST / HTTPS)
                         v                          v
+-----------------------------------------------------------------------------------+
|            HOSPEDAGEM E PROCESSAMENTO EM NUVEM — RENDER PaaS (Porta 10000)        |
|   Proxy Reverso Assíncrono aiohttp (`app/cloud_server.py`):                       |
|   - `/ws` e `/` -> Servidor Reativo Flet (`app/main.py` na porta interna 8550)    |
|   - `/ecoapi/*` -> API Auxiliar de Câmera, Telemetria GPS e OAuth (porta 8552)    |
|   - `/healthz`  -> Monitoramento de Saúde e Disponibilidade Contínua              |
|   - Algoritmos Backend: Grafo de Maceió (Dijkstra), QuickSort, Hash Tables        |
+-----------+-----------------------------------+-----------------------------------+
            |                                   |
            v                                   v
+-----------------------------------+   +-------------------------------------------+
| ARMAZENAMENTO DE OBJETOS (R2)     |   | PROCESSAMENTO COGNITIVO MULTIMODAL (R3)   |
| Catbox CDN / Firebase Storage     |   | Google Gemini API (`gemini-1.5-flash` +   |
| - Fotos georreferenciadas (antes) |   | Pool de Failover Automático)              |
| - Evidências de limpeza (depois)  |   | - Auditoria comparativa antes vs. depois  |
+-----------------------------------+   +---------------------+---------------------+
                                                              |
                                                              v
+-----------------------------------------------------------------------------------+
|            PERSISTÊNCIA NoSQL DISTRIBUÍDA — GOOGLE CLOUD FIRESTORE (R2/R5)        |
|   Projeto GCP/Firebase: `ecobounty-9d250` (Plano Gratuito Spark)                  |
|   - Coleções: `bounties`, `users`, `transactions` (imutável) e `history`          |
|   - Governança: `firestore.rules` + Service Account montada em `/etc/secrets/`    |
+-----------------------------------------------------------------------------------+
```

### 4.1 Conexão entre as 4 Camadas de Software
1. **Camada de Apresentação (Frontend Flet & UI):** Construída em Python sobre o motor Flutter/Dart (CanvasKit Web e pacote Android TWA/APK), integrada ao mapa interativo Leaflet.js / OpenStreetMap HD.
2. **Camada de Aplicação e Serviços (*Service Layer*):** Orquestra a lógica de negócio e integração com a nuvem (`AuthService`, `BountyService`, `VisionService`, `WalletService`, `StorageService`, `FirestoreService` e `EcopontoService`).
3. **Camada de Domínio e Estruturas de Dados Avançadas:** Implementa o grafo ponderado `MaceioEcoGraph` com Dijkstra ($O((V+E)\log V)$), QuickSort com Mediana de Três ($O(N \log N)$), Tabelas Hash (`SeparateChainingHashTable` e `OpenAddressingHashTable` com Hash Duplo) e estruturas lineares (`CustomVector`, `LinkedList`, `DoublyLinkedList`, `RestrictedLinearList`, `Stack`, `Queue`, `Deque`).
4. **Camada de Persistência e Infraestrutura em Nuvem:** Integração em tempo real entre Render PaaS, Firebase Auth, Google Cloud Firestore, Catbox CDN e Google Gemini API, com contingência *Local-First* em SQLite.

### 4.2 Modelos de Serviço em Nuvem Empregados (IaaS, PaaS, BaaS e SaaS) — Etapa 2
- **PaaS (*Platform as a Service*) — Render Web Service:** Fornece o ambiente gerenciado de execução em Python 3.11 com build automatizado a partir do GitHub (`render.yaml`), certificado TLS/HTTPS nativo e proxy reverso, eliminando a necessidade de administrar sistemas operacionais ou máquinas virtuais.
- **BaaS / DBaaS (*Backend & Database as a Service*) — Google Cloud Firestore e Firebase Auth:** O Cloud Firestore atua como banco NoSQL orientado a documentos em tempo real, enquanto o Firebase Authentication gerencia o fluxo OAuth 2.0 (Google Sign-In) sem expor credenciais no servidor.
- **IaaS / Object Storage (*Infraestrutura de Armazenamento*) — Catbox CDN e Firebase Storage:** Infraestrutura de armazenamento persistente de objetos binários para guarda permanente e entrega via CDN das fotografias de auditoria ambiental.
- **SaaS (*Software / AI as a Service*) — Google Gemini Multimodal API:** Serviço gerenciado de Inteligência Artificial Multimodal consumido via REST API HTTPS para classificar resíduos e auditar a limpeza das áreas sem necessidade de provisionar GPUs próprias.

---

## 5. Serviços em Nuvem Utilizados e Justificativas

| Serviço em Nuvem | Modelo | Função Desempenhada no EcoBounty | Justificativa Técnica da Escolha |
| :--- | :---: | :--- | :--- |
| **Render (Web Service)** | PaaS | Hospedagem pública 24/7 (`https://ecobounty-app.onrender.com`) com manifesto `render.yaml`. | Suporte nativo a WebSockets, deploy contínuo via GitHub, healthcheck em `/healthz` e montagem segura de segredos em `/etc/secrets/`. |
| **Google Cloud Firestore (`ecobounty-9d250`)** | BaaS / NoSQL | Persistência em tempo real das coleções `bounties`, `users`, `transactions` e `history`. | Baixa latência, sincronização reativa multi-dispositivo e cota gratuita generosa (50.000 leituras e 20.000 escritas/dia no plano Spark). |
| **Firebase Authentication** | BaaS | Autenticação federada com Google Sign-In e controle de sessão. | Elimina armazenamento vulnerável de senhas, oferece login em 1 clique e garante conformidade com a LGPD. |
| **Catbox CDN Storage** | IaaS / Storage | Armazenamento permanente de fotos de denúncias e comprovantes de limpeza. | Upload multipart rápido via API REST com geração de URLs públicas permanentes sem custo de tráfego (*egress*). |
| **Google Gemini API (AI Studio)** | SaaS / IA | Auditoria visual comparativa *antes vs. depois* e classificação de resíduos. | Visão multimodal de alta precisão com plano gratuito no Google AI Studio e pool de *failover* automático entre modelos. |

### 5.1 Justificativa de Migração de Provedor e Restrição *Pay-to-Use* (Orientações do Edital)
Em cumprimento às orientações da disciplina (*"façam o possível com sistema gratuito; se encontrarem problemas relacionados com pay-to-use, relatem no relatório"*), registra-se que o portal Microsoft Azure exigiu vinculação de cartão e assinatura *Pay-As-You-Go* indisponível para a equipe acadêmica. Dessa forma, todos os conceitos e requisitos obrigatórios (**R1 a R6**) foram implementados com equivalência 1:1 em provedores de cota gratuita real:
- *Azure Resource Group* $\leftrightarrow$ Projeto Google Cloud / Firebase (`ecobounty-9d250`);
- *Azure Table Storage / Cosmos DB* $\leftrightarrow$ Google Cloud Firestore (NoSQL);
- *Azure Blob Storage* $\leftrightarrow$ Catbox CDN / Firebase Storage;
- *Azure App Service / Functions* $\leftrightarrow$ Render PaaS (`app/cloud_server.py`) + Google Gemini API.

---

## 6. Tecnologias e Linguagens Empregadas

- **Python 3.11.9:** Linguagem principal do backend, estruturas de dados, algoritmos e integração cloud.
- **Flet Framework 0.18.0 (Flutter/Dart Web & Android TWA):** Interface reativa multiplataforma acessível via navegador e APK Android.
- **aiohttp 3.9:** Proxy reverso assíncrono unificando WebSockets (`/ws`) e API HTTP auxiliar (`/ecoapi/*`) na porta única do Render.
- **Firebase Admin SDK 6.8 & `google-cloud-firestore` 2.14:** Comunicação autenticada com o ecossistema Google Cloud / Firebase.
- **Leaflet.js, OpenStreetMap HD e OSRM:** Mapa interativo com camadas de satélite/ruas e cálculo de rotas viárias reais.
- **Matplotlib 3.11 & Pillow:** Renderização científica do grafo viário de Maceió e curvas de benchmark de ordenação.
- **Pytest:** Suíte de testes automatizados com **123+ testes unitários e de integração** 100% aprovados.

---

## 7. Evidências da Implementação, da Nuvem e dos Testes

### 7.1 Validação dos 5 Cenários Obrigatórios de Nuvem (Etapa 5 do Edital)

| Cenário Obrigatório (Etapa 5) | Como Foi Testado e Validado no EcoBounty | Resultado Obtido |
| :--- | :--- | :---: |
| **1. Acesso à aplicação e API pela Internet** | Acesso público HTTPS em `https://ecobounty-app.onrender.com`, conexão WebSocket ativa (`/ws`) e verificação dos endpoints REST `/healthz` e `/ecoapi/status`. | **Aprovado (HTTP 200 / Live)** |
| **2. Inserção e armazenamento de dados** | Registro de denúncia com upload da foto na Catbox CDN e criação imediata do documento nas coleções `bounties`, `users` e `transactions` do Cloud Firestore (`ecobounty-9d250`). | **Aprovado (Persistido)** |
| **3. Processamento executado na nuvem** | Auditoria multimodal via API Google Gemini (comparando foto antes/depois), cálculo de menor caminho via Algoritmo de Dijkstra no servidor e divisão contábil 50/50. | **Aprovado (Auditado)** |
| **4. Recuperação e apresentação dos resultados** | Leitura em tempo real do Cloud Firestore atualizando o feed de missões, os pinos no mapa interativo Leaflet HD e o saldo da carteira digital. | **Aprovado (Sincronizado)** |
| **5. Comportamento diante de entrada inválida ou falha simples** | **(a) Entrada Inválida:** Foto sem lixo na denúncia ou local ainda sujo na Fase 1 é reprovada pela IA (`approved: false`), bloqueando o pagamento; tentativa de aceitar a 6ª missão simultânea é bloqueada pela `RestrictedLinearList`.<br>**(b) Falha Simples:** Em erro de cota/rede da IA (*HTTP 429/503*), o `VisionService` aciona *failover* automático para o próximo modelo do pool; em duplo clique financeiro, a chave de idempotência (`advance_{user_id}_{bounty_id}`) impede pagamento duplicado. | **Aprovado (Resiliente)** |

### 7.2 Evidências dos Painéis de Nuvem (Entregável C)
1. **Render PaaS Dashboard:** Serviço `ecobounty-app` com status `Deploy succeeded | Live`, executando `python -m app.cloud_server` na porta pública `10000` em `https://ecobounty-app.onrender.com`.
2. **Firebase Cloud Firestore Console:** Banco `(default)` no plano **Spark (Sem custos)** exibindo as coleções `bounties`, `transactions` e `users` com documentos reais sincronizados.
3. **Firebase Authentication Console:** Provedor Google OAuth 2.0 ativo com os usuários autenticados da equipe (`kauelucasbarbosa979@gmail.com`, `gabrielholallan09@gmail.com`, `mathiasbm377@gmail.com`).
4. **Google AI Studio (API Gemini):** Painel de telemetria no **Nível gratuito** comprovando ~150 requisições reais processadas na chave `EcoBountyGAPI` com **100% de taxa de sucesso**.

---

## 8. Segurança, Consumo e Estimativa de Custos

### 8.1 Segurança da Informação (R6)
- **Zero Credenciais no Código-Fonte:** O repositório público ([`MathiasBorges/ecobounty-cloud`](https://github.com/MathiasBorges/ecobounty-cloud)) não expõe nenhuma chave ou senha. Todas as credenciais são injetadas via variáveis de ambiente (`.env` listado no `.gitignore` e documentado em `.env.example`) e, em produção no Render, via Secret Files em `/etc/secrets/serviceAccountKey.json`.
- **Imutabilidade Contábil (`firestore.rules`):** A coleção `transactions` possui bloqueio explícito de adulteração (`allow update, delete: if false;`), garantindo integridade de auditoria.
- **Autenticação Federada Google Auth:** O login utiliza tokens OAuth 2.0 assinados pelo Google, eliminando exposição de senhas.

### 8.2 Consumo Real e Estimativa de Custos
| Serviço em Nuvem | Consumo Registrado / Estimado | Cota Gratuita (Free Tier) | Custo Efetivo |
| :--- | :--- | :--- | :---: |
| **Render Web Service** | Hospedagem contínua com proxy reverso | 750 horas/mês (Plano Free) | **R$ 0,00** |
| **Google Cloud Firestore** | ~15.000 leituras e ~4.000 escritas/mês | 50.000 leituras e 20.000 escritas/dia | **R$ 0,00** |
| **Firebase Authentication** | Autenticação Google OAuth 2.0 | 50.000 MAUs gratuitos/mês | **R$ 0,00** |
| **Catbox CDN Storage** | Fotos de denúncias e limpezas (~42 MB) | Armazenamento permanente gratuito | **R$ 0,00** |
| **Google Gemini Multimodal API** | ~150 auditorias visuais realizadas nos testes | Nível Gratuito Google AI Studio | **R$ 0,00** |

---

## 9. Conclusão, Dificuldades e Possíveis Melhorias

### 9.1 Conclusão
O projeto **EcoBounty** comprovou na prática como a integração entre **Computação em Nuvem** (PaaS, BaaS/NoSQL, Object Storage e SaaS de IA) e **Estruturas de Dados Avançadas** viabiliza uma aplicação pública, escalável, auditável e de custo zero para enfrentar o desafio real da limpeza urbana e logística reversa em Maceió.

### 9.2 Principais Dificuldades Enfrentadas
- **Restrições *Pay-to-Use* em Provedores Tradicionais:** Contornadas pela migração arquitetural para o plano gratuito do Firebase Spark, Render PaaS e Google AI Studio.
- **Roteamento de Porta Única no Render:** Resolvido com a construção do proxy reverso assíncrono `aiohttp` (`app/cloud_server.py`) multiplexando WebSockets do Flet e rotas REST da câmera/GPS na mesma porta pública.
- **Limites de Taxa (*Rate Limits*) na API de IA:** Mitigados pela implementação de um pool de *failover* automático de modelos Gemini no `VisionService`.

### 9.3 Melhorias Futuras
- Integração via Webhook com a **ALURB / Prefeitura de Maceió** para despacho de caminhões em ocorrências de grande volume;
- Liquidação financeira automatizada via API Pix (Open Finance do Banco Central) diretamente para as contas dos coletores cooperados;
- Estimativa volumétrica de resíduos ($\text{m}^3$) por visão computacional 3D.
