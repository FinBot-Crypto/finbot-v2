# 🧪 fb-ml-validation

Microserviço responsável pela validação técnica e backtesting de modelos recém-treinados antes de sua promoção para o ambiente de execução real.

## 🎯 Objetivo
O `fb-ml-validation` atua como o controle de qualidade (Quality Gate) da inteligência do bot. Ele garante que um modelo só seja utilizado para tomar decisões financeiras se demonstrar performance estatística superior a um threshold pré-definido em dados que não foram usados no treinamento.

## 🚀 Funcionalidades
- **Backtesting em Tempo Real**: Carrega modelos do volume compartilhado e testa contra os dados mais recentes do mercado.
- **Métricas de Performance**: Calcula acurácia, precisão e recall (atualmente focado em acurácia direcional).
- **Quality Gate**: Reprova modelos que não atingem o mínimo de performance (ex: 60% de acurácia).
- **Auto-Promoção**: Notifica o ecossistema via NATS (`ml.model.validated`) quando um modelo é aprovado para uso em produção.

## 🔄 Fluxo CI/CD
1. **Push para `main`**: Dispara o workflow de deploy automático.
2. **Build Docker**: Instala pacotes de ciência de dados.
3. **Deploy via SSH**: Atualiza o serviço na VPS.
4. **Volume Compartilhado**: Acessa `/app/models` (o mesmo volume do `fb-ml-training`) para ler os arquivos `.joblib`.

## 🔑 Variáveis e Secrets Necessárias
| Nome | Descrição | Local |
|------|-----------|-------|
| `NATS_URL` | Endereço do NATS | `.env` |
| `MODELS_DIR` | Caminho para ler os modelos | Docker |
| `VPS_SSH_*` | Credenciais da VPS | GitHub Secrets |

## 🏗️ Infraestrutura Utilizada
- **NATS JetStream**: Escuta `ml.training.finished`.
- **Docker Volumes**: Compartilhamento de arquivos entre containers de treino e validação.
- **Scikit-Learn/Joblib**: Para carregamento e inferência de modelos.

## 📡 Fluxo de Mensagens
1. **Consome**: `ml.training.finished` (disparado pelo Treinador).
2. **Produz**: `ml.model.validated` (caso o modelo seja aprovado).

---
*FinBot-Crypto - ML Validation & Quality Gate*
