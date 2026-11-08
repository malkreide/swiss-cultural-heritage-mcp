## Finding: ARCH-005 — Keine Hardcoded Secrets: Env-Vars / Secret Manager only

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-005` |
| **PDF-Reference** | Sec 2.1 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Die Kernkriterien (keine Secrets in Code, History oder Image, keine Secret-Defaults, keine Secret-Logs) sind mit Werkzeug und Negativkontrolle belegt. Kriterien 3/4 (Laden aus Env, SecretStr) sind n/a, weil der Server keine Secrets braucht. Von den sechs anwendbaren Kriterien fehlen drei Hygiene-Punkte (6 .gitignore, 7 .env.example, 8 CI-Scan) -> 3 von 6 = 50 % -> partial. Kein Gap erreicht Severity critical; ein Leak liegt nicht vor.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-005.md`, Pass Criteria):

- [ ] Keine API-Keys, Passwörter, Tokens, Connection-Strings im Source-Code
- [ ] Keine Default-Werte mit echten Secrets in `os.environ.get(..., default=...)` oder ähnlich
- [ ] Secrets werden zur Startzeit aus Env-Vars / Secret-Manager geladen (Pydantic-Settings o.ä.)
- [ ] In-Memory-Repräsentation als `SecretStr` (Python) oder gleichwertig (kein `str`)
- [ ] Secrets erscheinen **nicht** in Log-Outputs (keine `f"{settings}"`-Logs)
- [ ] `.gitignore` enthält `.env`, `.env.*` (ausser `.env.example`)
- [ ] `.env.example` mit Platzhaltern existiert und ist im Repo
- [ ] CI-Workflow mit Gitleaks oder Trufflehog läuft auf PRs

### Evidence

- `gitleaks git . --redact` (v8.30.1) auf dem Repo: '142 commits scanned ... no leaks found', Report []; Negativkontrolle: Wegwerf-Repo im Scratchpad mit AWS-Key und ghp_-Token -> 'leaks found: 2'
- `git grep -nIE "(api[_-]?key|password|secret|token).*=.*[\"'][^\"']{16,}[\"']" HEAD -- src scripts Dockerfile server.json claude_desktop_config.json .github` -> einziger Treffer server.py:1184 `token_el = root.find(".//oai:resumptionToken", OAI_NS)` (OAI-Resumption-Token, kein Secret); Negativkontrolle `API_KEY = "sk-1234567890abcdef1234"` -> Treffer. Connection-String-/AKIA-/ghp_-/sk--Muster über ganz HEAD -> rc=1
- src/swiss_cultural_heritage_mcp/server.py:202, 228 — die einzigen Env-Zugriffe ausserhalb Settings: os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT') ohne Default, os.getenv('DEPLOYMENT_ENV', 'production'), kein Secret-Default; Settings src/swiss_cultural_heritage_mcp/server.py:65-150 hat keine Credential-Felder (auth_model none, Open Data)
- Dockerfile:34-38 (HEAD) — ENV nur PYTHONDONTWRITEBYTECODE, PYTHONUNBUFFERED, MCP_HOST, MCP_PORT; kein Secret im Image-Layer
- `git show HEAD:.gitignore` -> __pycache__/, *.py[cod], *.egg-info/, .pytest_cache/, .coverage*, htmlcov/, dist/, build/, .venv/, venv/: kein `.env`-Eintrag; `git ls-files | grep -iE '(^|/)\.env'` -> rc=1 (weder .env noch .env.example)
- `git grep -nIE 'gitleaks|trufflehog|secret.scan|detect-secrets' HEAD -- .github` -> rc=1: kein Secret-Scan in CI (ci.yml, nightly-live.yml, publish.yml)

### Gaps

- medium: kein automatisierter Secret-Scan (gitleaks/trufflehog) in einem PR-Workflow
- low: `.gitignore` schliesst `.env`/`.env.*` nicht aus; Settings liest zwar keine .env-Datei, eine lokal angelegte .env wäre aber commitbar
- low: kein `.env.example` mit den MCP_*-Variablen (bei auth_model none ohne Secrets, fehlt aber als Konfig-Referenz)

### Risk Description

Siehe Gaps; Severity laut Katalog `critical`. Katalogbeschreibung:

Hardcoded Secrets (API-Keys, Passwörter, Tokens, Connection-Strings, Encryption-Keys) im Source-Code sind die häufigste vermeidbare Sicherheitsschwäche in MCP-Server-Repositories. Sobald das Repo öffentlich ist (oder versehentlich öffentlich wird), oder ein Mitarbeiter aus dem Team ausscheidet, sind alle Secrets kompromittiert.

GitHub's Secret-Scanning fängt einen Teil davon ab — aber: (1) nicht alle Pattern werden erkannt, (2) Custom-API-Keys (z.B. interne Schulamt-APIs) sind unbekannt, (3) selbst nach Erkennung ist der Schlüssel bereits im Git-Verlauf und muss neu ausgestellt werden.

**Risiko-Eskalation:**

1. Klartext im Code → Public Repo → globaler Leak
2. Klartext in Env-Vars im Code → docker-compose.yml im Repo → gleicher Leak
3. Env-Vars-Referenz im Code, .env-Datei nicht in .gitignore → Leak via PR
4. Korrekte .gitignore, aber Klartext in CI-Logs → Leak via Public Actions
5. Korrekte CI-Maskierung, aber Klartext in Container-Image-Layer → Leak via Docker-Hub

Der Best-Practice-Standard für Production ist: **Env-Vars als Minimum, Secret-Manager als Empfehlung.**

### Remediation

Aus dem Katalog (`checks/ARCH-005.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Bestehende Secrets identifizieren und ersetzen

```bash
# Lokale Suche (vor jeglichem Push)
gitleaks detect --source . --verbose

# Falls schon committed: History-Rewrite ZUSÄTZLICH zur Schlüssel-Rotation
# Wichtig: rotation FIRST, history-rewrite zweitrangig
```

### Schritt 2: Migration zu Pydantic-Settings

```python
# Vorher
API_KEY = "sk-1234..."

# Nachher
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: SecretStr
    model_config = {"env_file": ".env", "extra": "forbid"}

settings = Settings()
# Im Code: settings.api_key.get_secret_value()
```

### Schritt 3: `.env.example` mit Platzhaltern

```bash
# .env.example (committet)
API_KEY=replace-with-real-key
DATABASE_URL=postgresql://user:pass@localhost/dbname
OAUTH_CLIENT_SECRET=at-least-32-characters-long-secret

# .env (NICHT committet, in .gitignore)
API_KEY=sk-actual-real-key
...
```

### Schritt 4: Production-Secret-Manager (höhere Reife)

| Plattform | Mechanismus |
|---|---|
| Railway | Project-Variables (verschlüsselt at-rest) |
| Render | Environment-Groups |
| Kubernetes | `Secret`-Objects + `secretKeyRef` in Pod-Spec |
| Self-Hosted | HashiCorp Vault, AWS Secrets Manager (EU-Region!), GCP Secret Manager |

```python
# AWS Secrets Manager (EU-Region für DSG, siehe CH-001)
import boto3
import json

def load_secret(name: str) -> dict:
    client = boto3.client("secretsmanager", region_name="eu-central-1")
    response = client.get_secret_value(SecretId=name)
    return json.loads(response["SecretString"])

secrets = load_secret("schulamt-mcp/production")
api_key = secrets["api_key"]
```

### Schritt 5: CI-Scan einrichten

Siehe Modus 5 oben.

### Schritt 6: Pre-Commit-Hook lokal

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

```bash
pre-commit install
# Verhindert Commits mit erkannten Secrets lokal
```

### Effort Estimate

Katalog-Richtwert (checks/ARCH-005.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S–M — Bei sauberem Repo: < 1 Tag (Settings-Migration + CI-Setup). Bei Repo mit Secret-Leak in History: 2–3 Tage (Rotation aller Schlüssel, History-Rewrite, Audit aller Forks/Clones).
