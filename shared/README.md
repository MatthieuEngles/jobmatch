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


## Embeddings integration tests ⚠️

The repository includes an optional integration test that exercises a real
`sentence-transformers` model. This test is disabled by default so CI and
local runs remain fast.

To run it locally:

```bash
# Install the optional extras (this will pull heavy deps like torch):
pip install -e .[embeddings]

# Enable the test by setting the env var and run pytest for the embeddings package:
JOBMATCH_RUN_EMBEDDING_INTEGRATION=1 pytest shared/src/shared/embeddings -q
```

The test uses a small default model (`all-MiniLM-L6-v2`) to reduce resource
usage but still provides a realistic runtime check that the end-to-end
integration works.


## Demo script 🧪

A small demo script is available to quickly try out similarity computations:

```bash
python shared/scripts/embeddings_demo.py
```

The script runs a tiny, deterministic `simple_embedder` and — if
`sentence-transformers` is installed — will also run a demo using a real
model (`all-MiniLM-L6-v2`) and print pairwise and joint similarity scores.
