-- Generated INSERT statements for users
INSERT INTO users (
    email,
    hashed_password,
    is_active,
    is_superuser,
    roles,
    created_at
  )
VALUES (
    'alice@example.com',
    '$pbkdf2-sha256$29000$0Fpr7T0HQIix1npPCcFYyw$2/J/Rn5btOETngoU2/SaRc8AkHmfKKaM5aKw/V7Mwwk',
    true,
    false,
    'viewer',
    '2026-02-08T19:43:31.756589+00:00'
  );
INSERT INTO users (
    email,
    hashed_password,
    is_active,
    is_superuser,
    roles,
    created_at
  )
VALUES (
    'bob@example.com',
    '$pbkdf2-sha256$29000$J8R4z3lPidHaW4vxXktpDQ$BSw3OMMWDHb5.LKPIhn/hLg0d1erFaPbto0FX893tqU',
    true,
    false,
    'viewer',
    '2026-02-08T19:43:31.756589+00:00'
  );
INSERT INTO users (
    email,
    hashed_password,
    is_active,
    is_superuser,
    roles,
    created_at
  )
VALUES (
    'admin@example.com',
    '$pbkdf2-sha256$29000$jlHKGWPs/b93bs05hxBiDA$OPXH/o4xeWqnw.RiOh2mwEG5U.Y7GhR3M1I9jT6qblI',
    true,
    true,
    'admin',
    '2026-02-08T19:43:31.756589+00:00'
  );