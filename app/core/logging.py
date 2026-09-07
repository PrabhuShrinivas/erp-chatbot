import logging
import os

def setup_logging():
    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # Explicitly enable SQLAlchemy query logging if DEBUG
    if level == logging.DEBUG:
        sql_logger = logging.getLogger('sqlalchemy.engine')
        sql_logger.setLevel(logging.INFO)
        if not sql_logger.handlers:
            import sys
            
            class SQLFormatter(logging.Formatter):
                def format(self, record):
                    record.msg = str(record.msg).replace('\n', ' ').strip()
                    return super().format(record)
                    
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(SQLFormatter('%(asctime)s [SQL] %(message)s'))
            sql_logger.addHandler(ch)
        
    return logging.getLogger("erp_qa")
