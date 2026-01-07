# Wasteless.io

> **Autonomous cloud cost optimization. From detection to execution.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Status](https://img.shields.io/badge/Status-Production--Ready-brightgreen.svg)]()

---

## 🎯 The Problem

Companies waste **20-40% of their cloud budget** on idle resources, oversized instances, and forgotten environments.

Traditional tools show you the waste. **Wasteless eliminates it automatically.**

CFOs don't want dashboards. **They want their money back.**

---

## 💡 The Solution

Wasteless.io is an **autonomous cloud cost optimization platform** that detects, executes, and verifies savings.

### What Makes Us Different

| Traditional Tools | Wasteless.io |
|------------------|--------------|
| Detection only | **Detection + Execution** |
| Manual optimization | **Autonomous remediation** |
| "Here's the waste" | **"We saved €15k this month"** |
| Hope + spreadsheets | **Verified savings tracking** |
| No accountability | **Measured ROI with proof** |

**The breakthrough:** We don't just recommend. We execute and prove the savings.

---

## ✨ What's Actually Built (MVP)

This is a **production-ready MVP** with enterprise-grade safeguards.

### Core Features

#### 🔍 **Detection Engine**
- **CloudWatch Metrics Collection** - CPU, network I/O, instance metadata (7-day lookback)
- **EC2 Idle Detection** - Identifies instances with <5% CPU utilization
- **Confidence Scoring** - Smart waste classification (0.0-1.0 confidence)
- **Intelligent Recommendations** - Terminate/Stop/Downsize based on confidence

#### ⚡ **Execution Engine**
- **Autonomous Remediation** - Stops idle EC2 instances automatically
- **7-Layer Safeguards** - Multi-checkpoint protection system
- **Rollback Snapshots** - Full state backup before any action
- **Dry-Run Mode** - Test everything before going live
- **Configuration-Driven** - YAML-based policies (no code changes)

#### 🛡️ **Safeguard System**

Before executing ANY action, Wasteless validates:

1. **Global Kill Switch** - Auto-remediation enabled?
2. **Whitelist Protection** - Instance IDs or tags marked as critical?
3. **Age Validation** - Instance older than 30 days?
4. **Confidence Threshold** - Detection confidence ≥ 80%?
5. **Idle Duration** - Idle for 14+ consecutive days?
6. **Schedule Window** - Current time in allowed execution window?
7. **Blast Radius Control** - Under max instances per run limit (3)?

**If ANY check fails → action aborted + logged.**

#### 📊 **Verification Engine**
- **Savings Tracker** - Compares AWS Cost Explorer data before/after
- **Accuracy Measurement** - Actual vs. estimated savings percentage
- **ROI Proof** - Hard financial evidence of impact
- **Complete Audit Trail** - Every action logged with metadata

#### 💾 **Data Infrastructure**
- **PostgreSQL Database** - 7 tables storing metrics, waste, actions, savings
- **Metabase Dashboards** - Executive visibility into costs and savings
- **Docker Deployment** - Full stack containerized

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│             AWS Account (Your Cloud)            │
│  Cost Explorer API  │  CloudWatch API  │  EC2   │
└──────────────┬──────────────────────────────────┘
               │ Metrics & Cost Data
               ↓
┌─────────────────────────────────────────────────┐
│           Wasteless Platform (Local)            │
│                                                 │
│  ┌──────────────┐    ┌───────────────────────┐ │
│  │  COLLECTORS  │───→│   PostgreSQL          │ │
│  │  (Metrics)   │    │   7 Core Tables       │ │
│  └──────────────┘    └───────┬───────────────┘ │
│                              │                  │
│  ┌──────────────┐            │                  │
│  │  DETECTORS   │───────────→│                  │
│  │ (Idle EC2)   │            │                  │
│  └──────────────┘            │                  │
│                              │                  │
│  ┌──────────────┐            │                  │
│  │ REMEDIATORS  │←───────────┤                  │
│  │ (Stop EC2)   │            │                  │
│  └──────┬───────┘            │                  │
│         │                    │                  │
│         ↓                    ↓                  │
│  ┌──────────────┐    ┌──────────────┐          │
│  │   TRACKERS   │───→│   Metabase   │          │
│  │  (Savings)   │    │  (Dashboard) │          │
│  └──────────────┘    └──────────────┘          │
└─────────────────────────────────────────────────┘
```

### Data Flow

1. **Collect** → CloudWatch metrics → PostgreSQL (`ec2_metrics`)
2. **Detect** → Analyze idle patterns → `waste_detected`, `recommendations`
3. **Execute** → Safeguard validation → Stop instance → `actions_log`, `rollback_snapshots`
4. **Verify** → Cost Explorer comparison → `savings_realized`
5. **Visualize** → Metabase reads PostgreSQL → Executive dashboards

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- AWS Account with Cost Explorer enabled
- 15 minutes

### Installation

```bash
# 1. Clone repository
git clone https://github.com/wastelessio/wasteless.git
cd wasteless

# 2. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.template .env
# Edit .env with your AWS credentials

# 5. Start PostgreSQL + Metabase
docker-compose up -d

# 6. Wait for containers to initialize
sleep 30

# 7. Collect your first metrics
python src/collectors/aws_cloudwatch.py

# 8. Detect waste
python src/detectors/ec2_idle.py

# 9. Open Metabase
open http://localhost:3000
```

**Done!** You now have waste detection running on your AWS account.

---

## ⚙️ Configuration

### 1. AWS IAM Setup (Read-Only)

Create an IAM user with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ce:GetCostAndUsage",
      "ce:GetCostForecast",
      "cloudwatch:GetMetricStatistics",
      "cloudwatch:ListMetrics",
      "ec2:Describe*",
      "ec2:StopInstances",
      "ec2:StartInstances"
    ],
    "Resource": "*"
  }]
}
```

**Note:** `ec2:Stop/StartInstances` only needed if using auto-remediation.

### 2. Environment Variables

```bash
# AWS Configuration
AWS_REGION=eu-west-1
AWS_ACCOUNT_ID=123456789012
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wasteless
DB_USER=wasteless
DB_PASSWORD=wasteless_dev_2025

# Metabase
METABASE_URL=http://localhost:3000
```

### 3. Remediation Configuration

Edit `config/remediation.yaml` to control auto-remediation:

```yaml
auto_remediation:
  enabled: false              # Set to true to enable execution
  dry_run_days: 7            # Mandatory testing period

safeguards:
  min_instance_age_days: 30   # Don't touch new instances
  min_idle_days: 14           # Must be idle 14+ days
  min_confidence_score: 0.80  # 80% confidence required
  max_instances_per_run: 3    # Max 3 stops per execution

whitelist:
  instance_ids:
    - i-0123456789abcdef0     # Protected instances
  tags:
    Environment: production   # Protected by tags
    Critical: "true"

schedule:
  allowed_days: [Saturday, Sunday]
  allowed_hours: [2, 3, 4]    # 2-5 AM only
  timezone: Europe/Paris
```

**Safety First:** Auto-remediation is **disabled by default**. Test in dry-run mode first.

---

## 📖 Usage

### Collect Metrics

```bash
# Collect CloudWatch metrics for all EC2 instances
python src/collectors/aws_cloudwatch.py

# Verify data
docker exec -it wasteless-postgres psql -U wasteless -d wasteless \
  -c "SELECT instance_id, cpu_avg, metric_date FROM ec2_metrics LIMIT 5;"
```

### Detect Waste

```bash
# Run idle EC2 detection
python src/detectors/ec2_idle.py

# View detected waste
docker exec -it wasteless-postgres psql -U wasteless -d wasteless \
  -c "SELECT resource_id, monthly_waste_eur, confidence_score FROM waste_detected;"
```

### Execute Remediation

```bash
# Dry-run mode (no actual AWS actions)
python src/remediators/ec2_remediator.py --dry-run

# Live execution (only if enabled in config)
python src/remediators/ec2_remediator.py

# View action log
docker exec -it wasteless-postgres psql -U wasteless -d wasteless \
  -c "SELECT resource_id, action_type, action_status FROM actions_log;"
```

### Verify Savings

```bash
# Track actual savings (wait 7+ days after action)
python src/trackers/savings_tracker.py

# View verified savings
docker exec -it wasteless-postgres psql -U wasteless -d wasteless \
  -c "SELECT actual_savings_eur, savings_accuracy_percent FROM savings_realized;"
```

### View Dashboards

1. Open http://localhost:3000
2. First time: Create Metabase admin account
3. Connect to PostgreSQL:
   - Host: `postgres` (Docker network name)
   - Port: 5432
   - Database: wasteless
   - User/Password: wasteless / wasteless_dev_2025
4. Explore pre-built dashboards

---

## 📊 Database Schema

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ec2_metrics` | CloudWatch metrics snapshots | `instance_id`, `cpu_avg`, `cpu_max`, `network_in_mb`, `metric_date` |
| `waste_detected` | Identified waste opportunities | `resource_id`, `waste_type`, `monthly_waste_eur`, `confidence_score` |
| `recommendations` | Actionable optimizations | `recommendation_type`, `action_required`, `estimated_savings_eur`, `status` |
| `actions_log` | Remediation execution log | `action_type`, `action_status`, `dry_run`, `metadata`, `error_message` |
| `rollback_snapshots` | Pre-action state backups | `state_before` (JSON), `rollback_expiry`, `can_rollback` |
| `savings_realized` | Verified actual savings | `cost_before_eur`, `cost_after_eur`, `actual_savings_eur`, `savings_accuracy_percent` |
| `cloud_costs_raw` | Raw AWS cost data | `service`, `resource_id`, `cost`, `usage_date` |

**Design Principles:**
- JSONB for flexible metadata storage
- Foreign keys for referential integrity
- Automatic timestamps (`created_at`, `updated_at`)
- Complete audit trail for compliance

---

## 🗺️ Roadmap

### ✅ Phase 1 - EC2 Optimization (Complete)
- [x] CloudWatch metrics collection
- [x] EC2 idle detection (<5% CPU)
- [x] Autonomous stop remediation
- [x] Multi-layer safeguards
- [x] Rollback snapshots
- [x] Savings verification
- [x] PostgreSQL + Metabase
- [x] End-to-end testing

### 🔄 Phase 2 - Additional AWS Resources (Q1 2025)
- [ ] RDS idle database detection
- [ ] EBS orphaned volumes
- [ ] S3 bucket optimization
- [ ] Elastic IP waste detection
- [ ] Multi-account AWS support

### 📅 Phase 3 - Advanced Execution (Q2 2025)
- [ ] Instance rightsizing (not just stop)
- [ ] Environment scheduling (dev/staging auto-shutdown)
- [ ] Terraform integration (infrastructure as code)
- [ ] Slack/Teams notifications
- [ ] Custom remediation policies

### 📅 Phase 4 - Multi-Cloud (Q3-Q4 2025)
- [ ] Google Cloud Platform support
- [ ] Microsoft Azure support
- [ ] Kubernetes cluster optimization
- [ ] Cost forecasting & budgets
- [ ] Custom rules engine

---

## 🧪 Development

### Project Structure

```
wasteless/
├── src/
│   ├── collectors/           # Data collection
│   │   └── aws_cloudwatch.py
│   ├── detectors/            # Waste detection
│   │   └── ec2_idle.py
│   ├── remediators/          # Execution
│   │   └── ec2_remediator.py
│   ├── trackers/             # Verification
│   │   └── savings_tracker.py
│   └── core/                 # Shared utilities
│       ├── database.py
│       └── safeguards.py
├── sql/                      # Database schemas
│   ├── init.sql
│   └── migrations/
├── config/                   # Configuration
│   └── remediation.yaml
├── tests/                    # Test suite
│   └── test_end_to_end.py
├── docker-compose.yml        # Infrastructure
└── requirements.txt          # Dependencies
```

### Running Tests

```bash
# Run end-to-end integration tests
python tests/test_end_to_end.py

# Expected output: Full pipeline test with savings verification
```

### Tech Stack

- **Language:** Python 3.11+
- **Database:** PostgreSQL 16
- **BI Tool:** Metabase (open source)
- **Cloud SDK:** boto3 (AWS)
- **Infrastructure:** Docker Compose
- **Data Processing:** pandas, numpy
- **Configuration:** PyYAML

---

## 🛡️ Security & Safeguards

### Multi-Layer Protection

1. **Configuration Kill Switch** - Global enable/disable
2. **Whitelist Protection** - Instance IDs and tags
3. **Age Validation** - Don't touch new resources
4. **Confidence Thresholds** - Only act on high-confidence detections
5. **Idle Duration Gates** - Must be idle for extended period
6. **Schedule Restrictions** - Time-based execution windows
7. **Blast Radius Control** - Limit instances per run

### Rollback Capability

- **Automatic Snapshots** - State saved before every action
- **7-Day Retention** - Time to detect issues
- **One-Click Restore** - Emergency rollback available
- **Audit Trail** - Every action logged with metadata

### Data Security

- ✅ Read-only AWS access (detection only by default)
- ✅ No credentials in code
- ✅ Environment variables for secrets
- ✅ Docker container isolation
- ✅ PostgreSQL authentication

**Security Issue?** Email: wasteless.io.entreprise@gmail.com

---

## 💼 Business Model

### Open Source Core (Apache 2.0)
Detection, execution, and basic dashboards are **free forever**.

### Enterprise Edition (Planned)
- Multi-cloud support (GCP, Azure)
- Advanced forecasting
- SLA on savings
- Priority support
- Custom integrations

### Pricing Philosophy
**Value-based:** 20-25% of verified savings.

**Example:**
- Detected waste: €100k/month
- Actual savings (verified): €70k/month
- Your cost: €17.5k/month (25%)

**→ Immediate ROI. Price becomes irrelevant.**

---

## 🤝 Contributing

We welcome contributions! This is an **open source project** making cloud optimization accessible to everyone.

### How to Contribute

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Areas Needing Help

- 🐛 Bug reports and fixes
- 📝 Documentation improvements
- ✨ New detection rules (RDS, EBS, S3)
- 🌍 Multi-cloud support (GCP, Azure)
- 🧪 Test coverage expansion
- 🎨 Metabase dashboard templates

---

## 📄 License

**Apache License 2.0** - See [LICENSE](LICENSE) for details.

**Why Apache 2.0?**
- Maximum adoption (permissive)
- Commercial use allowed
- Patent protection included
- Enterprise-friendly

---

## 📞 Contact & Support

- 📧 **Email:** wasteless.io.entreprise@gmail.com
- 💬 **GitHub Issues:** [Report bugs or request features](https://github.com/wastelessio/wasteless/issues)
- 🌐 **Website:** [Coming Soon]

---

## 🎯 Who Is This For?

### Ideal Users
- **Scale-ups** (100-500 employees) with growing cloud costs
- **CFOs/Finance Teams** who need verified savings, not dashboards
- **DevOps/Platform Teams** overwhelmed by manual optimization
- **Companies** spending €50k-500k/month on AWS

### Success Profile
You're a good fit if:
- Cloud costs are growing faster than revenue
- You have idle dev/staging environments
- Manual optimization is time-consuming
- You want accountability (verified savings)
- You need executive visibility

---

## 🚦 Project Status

**Version:** v0.1.0 (Production-Ready MVP)
**Status:** Active Development
**Last Updated:** January 2025
**Next Milestone:** Multi-resource detection (Q1 2025)

---

## 🙏 Acknowledgments

Built with world-class open source tools:
- [Metabase](https://www.metabase.com/) - Business intelligence
- [boto3](https://github.com/boto/boto3) - AWS SDK
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Docker](https://www.docker.com/) - Containerization

---

<p align="center">
  <strong>Stop monitoring waste. Start eliminating it.</strong>
  <br>
  Built with precision for CFOs who demand results.
</p>

---

## Quick Navigation

- [Installation](#-quick-start)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Architecture](#-architecture)
- [Database Schema](#-database-schema)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)
