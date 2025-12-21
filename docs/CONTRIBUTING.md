# Contributing to wasteless

First off, **thank you** for considering contributing to wasteless ! 🎉

Cloud cost optimization should be accessible to everyone. Your contributions help make that happen.

---

## 🎯 How Can I Contribute?

### 1. 🐛 Report Bugs

Found a bug? Help us fix it:

1. Check [existing issues](https://github.com/yourusername/wasteless/issues) first
2. If it's new, [open an issue](https://github.com/yourusername/wasteless/issues/new)
3. Include:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (OS, Python version, Docker version)
   - Relevant logs (anonymize sensitive data!)

### 2. 💡 Suggest Features

Have an idea? We'd love to hear it:

1. Check [roadmap](README.md#-roadmap) - maybe it's already planned
2. Open an issue with `[FEATURE]` prefix
3. Describe:
   - Problem you're solving
   - Proposed solution
   - Why it matters (business value)
   - Example use case

### 3. 📝 Improve Documentation

Documentation is just as important as code:

- Fix typos
- Clarify confusing sections
- Add examples
- Translate to other languages
- Create tutorials or blog posts

### 4. 💻 Write Code

Ready to code? Awesome!

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- AWS account (for testing)

### Setup Development Environment

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/wasteless.git
cd wasteless

# 3. Add upstream remote
git remote add upstream https://github.com/original/wasteless.git

# 4. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev tools (black, ruff, pytest)

# 6. Start Docker services
docker-compose up -d

# 7. Create .env from template
cp .env.template .env
# Edit .env with your AWS test credentials
```

---

## 🌿 Branch Strategy

### Main Branches

- `main` - Production-ready code, tagged releases
- `develop` - Integration branch for features

### Feature Branches

Create branches from `develop`:

```bash
git checkout develop
git pull upstream develop
git checkout -b feature/your-feature-name
```

**Branch naming**:
- `feature/add-rds-detector` - New features
- `bugfix/fix-postgres-timeout` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/simplify-cost-calc` - Code refactoring
- `test/add-collector-tests` - Tests

---

## ✍️ Commit Messages

Use clear, conventional commit messages:

**Format**: `type: description`

**Types**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting (no code change)
- `refactor:` Code restructuring
- `test:` Adding tests
- `chore:` Maintenance (deps, etc.)

**Examples**:
```bash
feat: add RDS idle instance detector
fix: PostgreSQL connection timeout after 1 hour
docs: add AWS setup troubleshooting guide
refactor: extract cost calculation to utils
test: add unit tests for EC2 detector
chore: update boto3 to 1.35.0
```

---

## 🧪 Code Standards

### Python Style

We use **Black** for formatting and **Ruff** for linting:

```bash
# Format code
black src/

# Lint
ruff check src/

# Fix auto-fixable issues
ruff check src/ --fix
```

### Code Quality Checklist

Before submitting PR:
- [ ] Code is formatted with Black
- [ ] No linting errors from Ruff
- [ ] Functions have docstrings (Google style)
- [ ] Complex logic has comments
- [ ] No hardcoded credentials or secrets
- [ ] Error handling is present
- [ ] Code is tested (manually or unit tests)

### Docstring Example

```python
def detect_idle_instances(self, cpu_threshold=5.0, days=7):
    """
    Detect EC2 instances with low CPU utilization.
    
    Args:
        cpu_threshold (float): CPU percentage threshold (default: 5.0%)
        days (int): Number of days to analyze (default: 7)
        
    Returns:
        list[dict]: List of idle instances with waste details
        
    Raises:
        DatabaseError: If cannot connect to PostgreSQL
        
    Example:
        >>> detector = WasteDetector()
        >>> idle = detector.detect_idle_instances(cpu_threshold=3.0)
        >>> print(f"Found {len(idle)} idle instances")
    """
    # Implementation
```

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_collectors.py

# Run with coverage
pytest --cov=src tests/
```

### Writing Tests

Create tests in `tests/` directory:

```python
# tests/test_waste_detector.py
import pytest
from src.detectors.ec2_idle import EC2IdleDetector

def test_detect_idle_instances():
    detector = EC2IdleDetector()
    # Use fixtures or mock AWS responses
    idle_instances = detector.detect_idle_instances(cpu_threshold=5.0)
    
    assert isinstance(idle_instances, list)
    assert all('instance_id' in inst for inst in idle_instances)
```

**Test Coverage Goals**:
- Core logic: 80%+
- Collectors: 60%+ (AWS API mocking)
- Detectors: 80%+

---

## 📥 Pull Request Process

### 1. Create Your Branch

```bash
git checkout develop
git pull upstream develop
git checkout -b feature/your-feature
```

### 2. Make Your Changes

- Write code
- Add tests (if applicable)
- Update documentation
- Format and lint

### 3. Commit Your Changes

```bash
git add .
git commit -m "feat: add RDS idle detector"
```

### 4. Push to Your Fork

```bash
git push origin feature/your-feature
```

### 5. Open Pull Request

1. Go to GitHub
2. Click "New Pull Request"
3. Base: `develop` ← Compare: `feature/your-feature`
4. Fill in PR template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring

## Testing
- [ ] Tested manually
- [ ] Added unit tests
- [ ] All tests pass

## Checklist
- [ ] Code formatted with Black
- [ ] No linting errors
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if relevant)

## Screenshots (if UI changes)
[Add screenshots]
```

### 6. Code Review

- Maintainers will review
- Address feedback
- Push updates to same branch
- PR auto-updates

### 7. Merge

Once approved:
- We'll merge to `develop`
- Periodically, `develop` → `main` for releases

---

## 🎨 Adding a New Waste Detection Rule

Want to add a new detector? Follow this template:

### 1. Create Detector File

```bash
touch src/detectors/your_detector.py
```

### 2. Implement Detector

```python
# src/detectors/rds_idle.py
from src.core.database import get_db_connection

class RDSIdleDetector:
    """Detects RDS instances with zero connections."""
    
    def __init__(self):
        self.conn = get_db_connection()
    
    def detect(self):
        """
        Detect idle RDS instances.
        
        Returns:
            list[dict]: Waste details
        """
        # Query CloudWatch metrics
        # Identify instances with 0 connections
        # Calculate waste
        # Return results
        pass
```

### 3. Add SQL Migration (if needed)

```bash
# sql/migrations/003_add_rds_metrics.sql
CREATE TABLE rds_metrics (
    id SERIAL PRIMARY KEY,
    instance_id VARCHAR(100),
    db_connections_avg DECIMAL(10,2),
    metric_date DATE NOT NULL
);
```

### 4. Update Documentation

- Add to README features list
- Document in `docs/ARCHITECTURE.md`
- Update roadmap if applicable

### 5. Test

```bash
python src/detectors/rds_idle.py
# Verify results in database
```

---

## 🌍 Multi-Cloud Support

Adding GCP or Azure support? Here's the structure:

```
src/collectors/
├── aws/
│   ├── costs.py
│   ├── cloudwatch.py
│   └── pricing.py
├── gcp/
│   ├── costs.py          # ← New
│   ├── monitoring.py     # ← New
│   └── pricing.py        # ← New
└── azure/
    └── ...
```

**Key principle**: Abstract interfaces

```python
# src/collectors/base.py
from abc import ABC, abstractmethod

class CostCollector(ABC):
    @abstractmethod
    def collect_costs(self, days=30):
        """Collect cost data for last N days."""
        pass
```

---

## 📋 Project Structure

```
wasteless-platform/
├── src/
│   ├── collectors/       # Data collection from cloud APIs
│   ├── detectors/        # Waste detection rules
│   ├── core/            # Shared utilities (DB, config, logging)
│   └── utils/           # Helper functions
├── sql/
│   ├── init.sql         # Initial schema
│   └── migrations/      # Schema evolution
├── dashboards/          # Metabase exports
├── docs/               # Documentation
├── tests/              # Unit and integration tests
└── scripts/            # Automation scripts
```

---

## 🐛 Debugging Tips

### PostgreSQL Issues

```bash
# Check if container is running
docker-compose ps

# View logs
docker-compose logs postgres

# Connect to database
docker exec -it wasteless-postgres psql -U wasteless -d wasteless

# Common queries
SELECT COUNT(*) FROM cloud_costs_raw;
SELECT * FROM waste_detected ORDER BY monthly_waste_eur DESC LIMIT 5;
```

### AWS API Issues

```bash
# Test credentials
aws sts get-caller-identity

# Test Cost Explorer access
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-02 \
  --granularity DAILY \
  --metrics UnblendedCost

# Enable debug logging in Python
export AWS_DEBUG=1
python src/aws_collector.py
```

### Python Debugging

```python
# Add to code
import pdb; pdb.set_trace()  # Breakpoint

# Or use print debugging
print(f"DEBUG: variable = {variable}")
```

---

## 🏆 Recognition

Contributors are recognized in:
- README.md contributors section
- CHANGELOG.md for their contributions
- GitHub contributors page

Significant contributors may be invited to become maintainers!

---

## 📜 Code of Conduct

Be respectful, inclusive, and constructive:
- Use welcoming language
- Respect differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community

Unacceptable behavior will not be tolerated.

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

---

**Thank you for making wasteless accessible to everyone!** 🚀

Every contribution, no matter how small, makes a difference.