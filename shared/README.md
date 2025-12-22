# JobMatch Shared

Shared interfaces and constants for JobMatch microservices.

## Installation

```bash
# From the shared directory
pip install -e .

# Or from another directory
pip install -e /path/to/shared
```

## Usage

```python
from shared.constants import ContentType
from shared.interfaces import ExtractedLine, CVData

# Create an extracted line
line = ExtractedLine(
    content_type=ContentType.SKILL_HARD,
    content="Python"
)

# Create CV data
cv = CVData(
    success=True,
    extracted_lines=[line]
)

# Use helpers
print(cv.skills_hard)  # ['Python']
```

## Contents

- `shared.constants.ContentType` - Enum of content types (skills, experience, etc.)
- `shared.interfaces.ExtractedLine` - A single extracted item from a CV
- `shared.interfaces.CVData` - Complete CV extraction result with helpers
- `shared.interfaces.ServiceHealth` - Standard health check response
