CREATE TABLE IF NOT EXISTS enduser (
	id SERIAL PRIMARY KEY,
	firstname TEXT NOT NULL,
	surname TEXT NOT NULL,
	email TEXT NOT NULL,
	username TEXT NOT NULL,
	password TEXT NOT NULL,
	ipaddr INET,
	currencycode TEXT
)WITH OIDS;
