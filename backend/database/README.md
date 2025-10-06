[init.py](init.py) can be used to initialize the PostgreSQL database with alembic migrations, optionally seed it with a SQL dump file, and upload files to an S3 bucket.
First follow the backend setup instructions to create a virtual environment, activate it and then navigate to the database folder. Then run:

```bash
python init.py --sql-dump dumps/dump.sql --s3-upload-dir dumps/s3
```

By default this backs up the database content before applying any changes. If the backup fails the script does not even start touching the database.  
The backup can be skipped using the `--no-backup` flag.