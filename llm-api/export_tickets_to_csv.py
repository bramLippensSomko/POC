import logging
from sqlalchemy import create_engine
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Replace with your MySQL credentials and database
engine = create_engine("mysql+pymysql://root:admin@localhost:3307/db")

query = """
SELECT
    i.id,
    i.subject,
    i.description,
    s.name AS status,
    p.name AS project_name,
    CONCAT(u.firstname, ' ', u.lastname) AS author,
    i.created_on
FROM
    issues i
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN projects p ON i.project_id = p.id
LEFT JOIN users u ON i.author_id = u.id
"""

# Read tickets from DB
df = pd.read_sql(query, engine)

# Clean up description and prepare content if needed
df["description"] = df["description"].fillna("").str.strip()
df["content"] = df["subject"].fillna("") + "\n\n" + df["description"]

# Filter only Goodmark tickets
goodmark_df = df[df["project_name"] == "Goodmark"]

# Export to CSV
output_file = "goodmark_tickets_export.csv"
goodmark_df.to_csv(output_file, index=False)

logger.info(f"Exported {len(goodmark_df)} Goodmark tickets to '{output_file}'")