CREATE TABLE athlete (
  StravaAthleteID NUMBER(19) NOT NULL PRIMARY KEY,
  firstname VARCHAR2(255),
  lastname VARCHAR2(255),
  firstlogin TIMESTAMP,
  lastlogin TIMESTAMP,
  access_token VARCHAR2(255),
  ref_token VARCHAR2(255),
  exp_at TIMESTAMP
);

