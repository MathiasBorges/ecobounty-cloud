# 🌱 EcoBounty — Economia Circular Gamificada e Plataforma em Nuvem para Logística Reversa Urbana

**Instituição:** Centro Universitário UNIMA — Afya (Maceió - AL)  
**Disciplina:** Computação em Nuvem (Cloud Computing) & Estruturas de Dados Avançadas  
**Integrantes:**
- **Allan Gabriel de Holanda Paz** — Arquitetura em Nuvem e Integração
- **Kaue Lucas Barbosa Silva** — Algoritmos, Estruturas de Dados e Backend
- **Mathias Borges Marques** — Serviços Cloud, Banco NoSQL e Testes Automatizados

---

## 🌐 Acesso Público da Aplicação em Nuvem (Produção)

- **Aplicação Web Hospedada (Render PaaS):** [https://ecobounty-app.onrender.com](https://ecobounty-app.onrender.com)
- **Endpoint de Saúde (Healthcheck Cloud):** [https://ecobounty-app.onrender.com/healthz](https://ecobounty-app.onrender.com/healthz)
- **Status de Telemetria / API Auxiliar:** [https://ecobounty-app.onrender.com/ecoapi/status](https://ecobounty-app.onrender.com/ecoapi/status)

---

## ☁️ Arquitetura em Nuvem e Modelos de Serviço (R1 a R6)

O **EcoBounty** resolve o problema real de descarte irregular de resíduos sólidos urbanos em Maceió (AL), conectando cidadãos denunciantes, coletores autônomos e a cooperativa **COOPLUM (Jacarecica)** por meio de uma arquitetura distribuída em nuvem com **Custo Operacional Zero (`R$ 0,00`)**:

| Camada / Serviço Cloud | Modelo de Nuvem | Papel na Arquitetura EcoBounty | Requisito Atendido |
| :--- | :---: | :--- | :---: |
| **Render Web Service (`render.yaml`)** | **PaaS** (*Platform as a Service*) | Hospedagem contínua em Python 3.11 com proxy reverso `aiohttp` (`app/cloud_server.py`) unificando WebSockets Flet e API REST em porta única. | **R1, R3, R4** |
| **Google Cloud Firestore (`ecobounty-9d250`)** | **BaaS / DBaaS** (*NoSQL*) | Persistência distribuída em tempo real das coleções `bounties`, `users`, `transactions` (imutável) e `history`. | **R1, R2, R5** |
| **Firebase Authentication (Google Auth)** | **BaaS** (*Identity as a Service*) | Login social federado OAuth 2.0 sem armazenamento local de senhas de contas Google. | **R4, R6** |
| **Catbox CDN / Firebase Storage** | **IaaS / Storage** (*Object Storage*) | Armazenamento persistente de objetos (fotos georreferenciadas de denúncias e comprovações de limpeza). | **R2, R5** |
| **Google Gemini Multimodal API** | **SaaS** (*AI as a Service*) | Processamento em nuvem por Visão Computacional comparando o *antes e depois* da limpeza e classificando resíduos sólidos. | **R3, R5** |

---

## 🧠 Estruturas de Dados e Algoritmos no Servidor

- **Grafo Ponderado (`app/algorithms/graphs.py`):** Malha viária de Maceió com **Algoritmo de Dijkstra** ($O((V + E) \log V)$) + roteamento urbano OSRM/Leaflet HD até o ecoponto ou cooperativa mais próxima.
- **Ordenação Rápida (`app/algorithms/sorting.py`):** **QuickSort com Mediana de Três** ($O(N \log N)$) para classificação de missões por recompensa, distância (Haversine) e urgência.
- **Tabelas Hash (`app/data_structures/hash_table.py`):** Encadeamento Separado para catálogo dinâmico de *bounties* e Endereçamento Aberto (Hash Duplo) para busca $O(1)$ de ecopontos.
- **Estruturas Lineares (`app/data_structures/`):** `RestrictedLinearList` (limite de 5 missões ativas por coletor), `Stack` LIFO (*Undo/Redo* de aceite), `Queue` FIFO e `Deque` (auditoria prioritária).

---

## 🔒 Segurança e Gestão de Credenciais (R6)

Em conformidade estrita com o **Requisito R6** e o **Entregável B**:
1. **Nenhuma credencial, token ou chave privada está exposta no código-fonte.**
2. Todas as configurações sensíveis são lidas via variáveis de ambiente (`os.getenv`) documentadas no arquivo [`.env.example`](.env.example).
3. No ambiente de produção (Render), a chave de conta de serviço do Firebase (`serviceAccountKey.json`) é montada de forma isolada em `/etc/secrets/` e as regras de acesso e imutabilidade financeira estão definidas em [`firestore.rules`](firestore.rules).

---

## 🚀 Como Executar o Projeto Localmente

### 1. Clonar o repositório e instalar dependências
```bash
git clone https://github.com/MathiasBorges/ecobounty-cloud.git
cd ecobounty-cloud
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente
Copie o arquivo de template `.env.example` para `.env`:
```bash
cp .env.example .env
```
*(A aplicação conta com padrão **Local-First**: mesmo sem chaves externas preenchidas no `.env`, ela executa integralmente com fallback local SQLite e simulação inteligente para fins de avaliação e testes).*

### 3. Iniciar a Aplicação
- **Modo Aplicação Web / Desktop (Flet):**
  ```bash
  python -m app.main
  ```
- **Modo Servidor Cloud com Proxy Reverso Unificado (como roda no Render):**
  ```bash
  python -m app.cloud_server
  ```
  Acesse no navegador: `http://localhost:8550`

---

## 🧪 Como Executar a Suíte de Testes Automatizados

O projeto possui cobertura automatizada via `pytest` validando todas as estruturas de dados, algoritmos de grafos/ordenação, integração com Google Cloud Firestore, Catbox CDN, Gemini Vision e fluxos de carteira digital:

```bash
python -m pytest tests/ -v
```

---

## 📄 Documentação Técnica

- [Relatório Técnico Oficial de Cloud Computing](Entregas/RELATORIO_TECNICO_CLOUD_ECOBOUNTY.md)
- [Guia de Configuração Google Cloud & Firebase](Entregas/GUIA_GOOGLE_CLOUD_FIREBASE.md)
- [Regras de Segurança do Cloud Firestore (`firestore.rules`)](firestore.rules)
- [Manifesto de Implantação PaaS (`render.yaml`)](render.yaml)
