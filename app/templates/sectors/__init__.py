"""Horn of Africa sector dashboard templates."""
from app.templates.sectors.humanitarian import HUMANITARIAN_TEMPLATES
from app.templates.sectors.igad import IGAD_TEMPLATES

ALL_SECTOR_TEMPLATES: list[dict] = HUMANITARIAN_TEMPLATES + IGAD_TEMPLATES
