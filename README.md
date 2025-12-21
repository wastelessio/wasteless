
# Wasteless.io

> **Stop monitoring cloud waste. Start eliminating it automatically.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Status](https://img.shields.io/badge/Status-MVP-yellow.svg)]()

---

## 🎯 The Problem

Companies waste **20-40% of their cloud budget** on idle resources, oversized instances, and forgotten environments. 

Existing tools like AWS Cost Explorer show you the waste. **They don't fix it.**

CFOs don't want more dashboards. **They want actual savings.**

---

## The Solution

Wasteles.io **detects AND executes** cloud optimizations automatically.

We don't just recommend. **We reduce your bill.**

### What makes us different

| Traditional wasteless Tools | Wasteles.io |
|--------------------------|----------------------------|
| Reporting |  **Execution** |
| Passive data | **Actionable recommendations** |
| "Here's the waste" | **"We saved you €15k this month"** |
| DevOps required | **Zero friction** |
| Monitoring-first | **Results-first** |

---

## ✨ Features (Phase 1 - MVP)

- ✅ **AWS Cost Collection** - Automatic daily cost ingestion via Cost Explorer API
- ✅ **EC2 Idle Detection** - Identifies instances with <5% CPU over 7 days
- ✅ **CloudWatch Metrics** - Collects CPU, network, and utilization data
- ✅ **Waste Calculation** - Estimates monthly savings with confidence scores
- ✅ **CFO Dashboards** - Metabase dashboards showing costs and savings opportunities
- ✅ **PostgreSQL Storage** - All data stored in structured, queryable format

### Coming Soon (Phase 2)

- ⏳ RDS idle instance detection
- ⏳ EBS orphaned volumes
- ⏳ Kubernetes over-provisioning analysis
- ⏳ Dev/staging environment scheduling
- ⏳ Multi-account AWS support

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- AWS Account with Cost Explorer enabled
- 30 minutes

### Installation

```bash
# 1. Clone repository
git clone https://github.com/wastelessio/wasteless-insfrastructure
cd wasteless

# 2. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.template .env
# Edit .env with your AWS credentials (see Configuration below)

# 5. Start PostgreSQL + Metabase
docker-compose up -d

# 6. Wait 30 seconds for containers to start
sleep 30

# 7. Run first data collection
python src/aws_collector.py

# 8. Open Metabase
open http://localhost:3000
```

**That's it!** Your first AWS cost data is now in PostgreSQL.

---

## ⚙️ Configuration

### 1. Create AWS IAM User (Read-Only)

The platform needs read-only access to your AWS account.

**In AWS Console:**
1. Go to IAM → Users → Add User
2. Name: `wasteless-readonly`
3. Access type: **Programmatic access**
4. Attach policies:
   - `ViewOnlyAccess`
   - Custom policy for Cost Explorer:

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
      "ec2:Describe*"
    ],
    "Resource": "*"
  }]
}
```

5. Download credentials CSV

### 2. Configure .env

```bash
# AWS Configuration
AWS_REGION=eu-west-1
AWS_ACCOUNT_ID=123456789012
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# Database (default values for local Docker)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wasteless
DB_USER=wasteless
DB_PASSWORD=wasteless_dev_2025

# Metabase
METABASE_URL=http://localhost:3000
```

⚠️ **Never commit `.env` to Git!** It's already in `.gitignore`.

### 3. Enable AWS Cost Explorer

If you see "not subscribed to AWS Cost Explorer":
1. Go to AWS Console → Cost Explorer
2. Click "Enable Cost Explorer"
3. Wait 24 hours for historical data (or continue with limited data)

---

## 📖 Usage

### Collect AWS Costs

```bash
# Collect last 30 days of AWS costs
python src/aws_collector.py

# Verify data in database
docker exec -it wasteless-postgres psql -U wasteless -d wasteless \
  -c "SELECT COUNT(*) FROM cloud_costs_raw;"
```

### Collect EC2 Metrics

```bash
# Collect CloudWatch metrics for EC2 instances
python src/aws_cloudwatch_collector.py
```

### Detect Waste

```bash
# Run waste detection (EC2 idle instances)
python src/waste_detector.py

# View detected waste
docker exec -it wasteless-postgres psql -U wasteless -d wasteless \
  -c "SELECT * FROM waste_detected;"
```

### Access Dashboards

1. Open http://localhost:3000
2. First time: Create admin account
3. Connect to PostgreSQL:
   - Host: `postgres` (container name, not localhost!)
   - Port: 5432
   - Database: wasteless
   - User/Password: wasteless / wasteless_dev_2025

4. Dashboards available:
   - **AWS Cost Overview** - Total costs, trends, top services
   - **Waste Detection** - Idle resources, savings opportunities

---

## 🏗️ Architecture

```
┌─────────────────┐
│   AWS Account   │
│  (Your Cloud)   │
└────────┬────────┘
         │ APIs (Cost Explorer, CloudWatch)
         ↓
┌─────────────────────────────────────┐
│     wasteless Platform (Local)         │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │  Collectors  │→ │ PostgreSQL  │ │
│  │   (Python)   │  │  Database   │ │
│  └──────────────┘  └──────┬──────┘ │
│                           │         │
│  ┌──────────────┐         │         │
│  │   Detectors  │────────→│         │
│  │   (Rules)    │         │         │
│  └──────────────┘         ↓         │
│                    ┌─────────────┐  │
│                    │  Metabase   │  │
│                    │ (Dashboards)│  │
│                    └─────────────┘  │
└─────────────────────────────────────┘
```

### Data Flow

1. **Collection**: Python scripts call AWS APIs daily
2. **Storage**: Raw data → PostgreSQL (`cloud_costs_raw`, `ec2_metrics`)
3. **Detection**: Waste detection rules analyze data
4. **Recommendations**: Actionable savings → `waste_detected`, `recommendations`
5. **Visualization**: Metabase reads PostgreSQL and displays dashboards

### Tech Stack

- **Language**: Python 3.11+
- **Database**: PostgreSQL 16
- **BI Tool**: Metabase (open source)
- **Cloud SDK**: boto3 (AWS)
- **Orchestration**: Docker Compose
- **Data Processing**: pandas

---

## 📊 Database Schema

### `cloud_costs_raw`
Raw cost data from AWS Cost Explorer
- Daily costs per service
- Granular usage tracking

### `ec2_metrics`
CloudWatch metrics for EC2 instances
- CPU utilization (avg, max)
- Network I/O
- 7-day rolling window

### `waste_detected`
Identified waste opportunities
- Resource ID, type, waste category
- Monthly waste amount (€)
- Confidence score (0-1)

### `recommendations`
Actionable cost optimizations
- Action required (stop, resize, delete)
- Estimated monthly savings
- Implementation effort (low/medium/high)

### `savings_realized`
Tracked savings after applying recommendations
- Actual vs. estimated savings
- Verification method

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed schema.

---

## 🗺️ Roadmap

### ✅ Phase 1 - MVP (Completed)
- [x] AWS cost collection
- [x] EC2 idle detection
- [x] Basic dashboards
- [x] PostgreSQL storage

### 🔄 Phase 2 - Additional Rules (Months 4-6)
- [ ] RDS idle detection
- [ ] EBS orphaned volumes
- [ ] S3 bucket analysis
- [ ] Kubernetes over-provisioning
- [ ] Multi-account support

### 📅 Phase 3 - Execution (Months 7-9)
- [ ] Terraform PR generation
- [ ] Environment scheduling (dev/staging)
- [ ] Optional auto-remediation
- [ ] Slack/Email alerts

### 📅 Phase 4 - Scale (Months 10-15)
- [ ] GCP support
- [ ] Azure support
- [ ] Cost forecasting
- [ ] Custom rules engine
- [ ] Enterprise RBAC

### 📅 Phase 5 - Market Fit (Months 16-24)
- [ ] Public API
- [ ] Terraform provider
- [ ] SaaS offering
- [ ] Multi-tenant support

---

## 🧪 Development

### Project Structure

```
wasteless-platform/
├── src/                    # Python source code
│   ├── collectors/         # AWS data collection
│   ├── detectors/          # Waste detection rules
│   ├── core/              # Shared utilities
│   └── utils/             # Helpers
├── sql/                   # Database schemas
│   ├── init.sql           # Initial schema
│   └── migrations/        # Schema changes
├── dashboards/            # Metabase exports
├── docs/                  # Documentation
├── tests/                 # Unit tests (TODO)
├── docker-compose.yml     # Local development
└── requirements.txt       # Python dependencies
```

### Running Tests

```bash
# TODO: Add pytest
pytest tests/
```

### Code Style

```bash
# Format code
black src/

# Lint
ruff check src/
```

### Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

---

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and data flow
- [AWS Setup](docs/AWS_SETUP.md) - Detailed IAM configuration
- [Development Guide](docs/DEVELOPMENT.md) - How to extend the platform
- [Deployment](docs/DEPLOYMENT.md) - Production deployment options

---

## 🤝 Contributing

Contributions are welcome! This is an **open source project** aimed at making cloud cost optimization accessible to everyone.

### How to contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Areas needing help

- 🐛 Bug reports and fixes
- 📝 Documentation improvements
- ✨ New waste detection rules
- 🌍 Multi-cloud support (GCP, Azure)
- 🧪 Test coverage
- 🎨 Dashboard improvements

---

## 💼 Business Model

### Open Source Core
The detection engine, collectors, and basic dashboards are **free and open source** (Apache 2.0).

### Enterprise Edition (Coming Soon)
- Auto-remediation
- Advanced forecasting
- SLA on savings
- Multi-tenant support
- Priority support

### Pricing (Planned)
**Value-based**: 20-25% of realized savings

Example:
- Detected waste: €100k/month
- Realized savings: €70k/month
- Your fee: €17.5k/month (25%)

→ **ROI is immediate. Price discussion is irrelevant.**

---

## 🛡️ Security

- ✅ Read-only AWS access (IAM policies)
- ✅ No credentials stored in code
- ✅ Environment variables for secrets
- ✅ Docker container isolation
- ✅ PostgreSQL with authentication

**Security issue?** Please email security@[yourdomain] (don't open public issue).

---

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

**Why Apache 2.0?**
- Maximum adoption (permissive)
- Commercial use allowed
- Patent protection included
- Compatible with enterprise requirements

---

## 🙏 Acknowledgments

- Built with [Metabase](https://www.metabase.com/) for business intelligence
- Uses [boto3](https://github.com/boto/boto3) for AWS integration
- Inspired by the [wasteless Foundation](https://www.wasteless.org/) principles

---

## 📞 Support & Contact

- 📧 Email: [wasteless.io.entreprise@gmail.com]
- 💬 GitHub Issues: [Report bugs or request features](https://github.com/yourusername/wasteless-platform/issues)
- 🐦 Twitter: [@wastelessio]
- 💼 LinkedIn: [Your Profile]

---

## ⭐ Star History

If this project helped you save money, please consider:
- ⭐ **Starring the repository**
- 🐦 **Sharing on social media**
- 📝 **Writing about your experience**

Every star motivates us to keep improving!

---

## 🎯 Target Audience

This platform is designed for:
- **Scale-ups** (100-400 employees) with growing cloud costs
- **CFOs** who need actual savings, not just visibility
- **DevOps teams** overwhelmed by manual optimization
- **Companies** spending €50k-300k/month on cloud

---

## 🚦 Status

**Current Version**: v0.1.0 (MVP)  
**Status**: Active Development  
**First Release**: January 2025  
**Production Ready**: Q2 2025 (planned)

---

<p align="center">
  <strong>Stop monitoring waste. Start eliminating it.</strong>
  <br>
  Built with ❤️ for CFOs who want results.
</p>

---

## Quick Links

- [Installation](#-quick-start)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Architecture](#-architecture)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)
