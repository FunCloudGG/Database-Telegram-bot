import psycopg2
import config
from config import logger

class Database:
    def __init__(self):
        self.dbname = config.dbname
        self.user = config.user
        self.password = config.password
        self.host = config.host
        self.port = config.port

    def get_connection(self):
        return psycopg2.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )

    def execute_query(self, query, params=None):
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
        except Exception as e:
            logger.error("Error in execute_query: %s", e)
        finally:
            if "cur" in locals():
                cur.close()
            if "conn" in locals():
                conn.close()

    def fetch_all(self, query, params=None):
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            return rows
        except Exception as e:
            logger.error("Error in fetch_all: %s", e)
            return []
        finally:
            if "cur" in locals():
                cur.close()
            if "conn" in locals():
                conn.close()

    # CLIENTS 
    def check_client_exists(self, client_number):
        query = "SELECT 1 FROM clients WHERE client_number = %s"
        rows = self.fetch_all(query, (client_number,))
        return len(rows) > 0

    def check_phone_exists(self, phone_number):
        query = "SELECT 1 FROM clients WHERE phone_number = %s"
        rows = self.fetch_all(query, (phone_number,))
        return len(rows) > 0

    def add_client_in_db(self, client_number, name, surname, status, phone_number=None):
        query = "INSERT INTO clients (name, surname, client_number, status) VALUES (%s, %s, %s, %s)"
        params = [name, surname, client_number, status]
        if phone_number is not None:
            params.append(phone_number)
            query = "INSERT INTO clients (name, surname, client_number, status, phone_number) VALUES (%s, %s, %s, %s, %s)"
        self.execute_query(query, params)
        if self.check_client_exists(client_number):
            logger.info("Added client: %s %s, number: %s", name, surname, client_number)
        return self.check_client_exists(client_number)

    def remove_client_from_db(self, client_number):
        client = self.get_client(client_number)
        query = "DELETE FROM clients WHERE client_number = %s"
        params = (client_number,)
        self.execute_query(query, params)
        if not self.check_client_exists(client_number):
            logger.info("Removed client: %s", client)
        return not self.check_client_exists(client_number)

    def get_client(self, client_number):
        query = "SELECT * FROM clients WHERE client_number = %s"
        params = (client_number,)
        row = self.fetch_all(query, params)
        return row[0] if row else None

    def show_client_in_db(self, client_number):
        row = self.get_client(client_number)
        if row:
            client = f"{row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[-1]}"
            return client
        return "Client not found."

    def update_client_in_db(
        self,
        old_client_number,
        new_client_number=None,
        new_name=None,
        new_surname=None,
        phone_number=None,
        new_status=None,
    ):
        client = self.get_client(old_client_number)
        query = "UPDATE clients SET client_number = %s,"
        parms = []
        if new_client_number is None:
            new_client_number = old_client_number
        parms.append(new_client_number)
        if new_name:
            query += " name = %s,"
            parms.append(new_name)
        if new_surname:
            query += " surname = %s,"
            parms.append(new_surname)
        if phone_number:
            query += " phone_number = %s,"
            parms.append(phone_number)
        if new_status:
            query += " status = %s,"
            parms.append(new_status)
        query = query.rstrip(",") + " WHERE client_number = %s"
        parms.append(old_client_number)
        self.execute_query(query, parms)
        if self.check_client_exists(new_client_number):
            logger.info("Updated client from: %s to: %s", client, self.get_client(new_client_number))
        return self.check_client_exists(new_client_number)

    def show_all_clients(self):
        rows = self.fetch_all("SELECT * FROM clients")
        return (
            "\n".join(
                [
                    " | ".join(str(val) for i, val in enumerate(row) if i not in (0, 5, 6))
                    for row in rows
                ]
            )
            if rows
            else "No data."
        )

    # TARIFFS 
    def show_all_tariffs(self):
        rows = self.fetch_all("SELECT * FROM tariffs WHERE type = %s", (False,))
        return (
            "\n".join([" | ".join(map(str, row[:-1])) for row in rows])
            if rows
            else "No data."
        )

    def show_all_tariff_types(self):
        rows = self.fetch_all("SELECT * FROM tariffs WHERE type = %s", (True,))
        return (
            "\n".join([" | ".join(map(str, row[:2])) for row in rows])
            if rows
            else "No data."
        )

    def check_tariff_type_exists(self, tariff_name):
        query = "SELECT 1 FROM tariffs WHERE name = %s AND type = %s"
        rows = self.fetch_all(query, (tariff_name, True))
        return len(rows) > 0

    def add_tariff_in_db(self, tariff_name, price, valid_from, valid_to=None):
        query = "INSERT INTO tariffs (name, price, valid_from"
        params = [tariff_name, price, valid_from]
        if valid_to:
            query += ", valid_to"
            params.append(valid_to)
        query += ") VALUES (%s, %s, %s"
        if valid_to:
            query += ", %s"
        query += ")"
        self.execute_query(query, params)
        rows = self.fetch_all(
            "SELECT 1 FROM tariffs WHERE name = %s AND price = %s",
            (tariff_name, price),
        )
        if self.check_tariff_exists(rows[0][0] if rows else None):
            logger.info("Added tariff: %s, price: %s, valid from: %s, valid to: %s", tariff_name, price,  valid_from, valid_to)
        return len(rows) > 0

    def add_tariff_type_in_db(self, tariff_name):
        query = "INSERT INTO tariffs (name, type) VALUES (%s, %s)"
        params = [tariff_name, True]
        self.execute_query(query, params)
        if self.check_tariff_type_exists(tariff_name):
            logger.info("Added tariff type: %s", tariff_name)
        return self.check_tariff_type_exists(tariff_name)

    def check_tariff_exists(self, tariff_id):
        query = "SELECT 1 FROM tariffs WHERE id = %s AND type = %s"
        rows = self.fetch_all(query, (tariff_id, False))
        return len(rows) > 0

    def show_tariff_in_db(self, tariff_id):
        query = "SELECT * FROM tariffs WHERE id = %s"
        params = (tariff_id,)
        row = self.fetch_all(query, params)
        if row:
            tariff = f"{row[0][0]} | {row[0][1]} | {row[0][2]} | {row[0][3]} | {row[0][4]}"
            return tariff
        return "Tariff not found."

    def remove_tariff_from_db(self, tariff_id):
        query = "DELETE FROM tariffs WHERE id = %s"
        params = (tariff_id,)
        self.execute_query(query, params)
        if not self.check_tariff_exists(tariff_id):
            logger.info("Removed tariff with ID: %s", tariff_id)
        return not self.check_tariff_exists(tariff_id)

    def check_associated_tariffs(self, tariff_name):
        query = "SELECT 1 FROM tariffs WHERE name = %s AND type = %s"
        rows = self.fetch_all(query, (tariff_name, False))
        return len(rows) > 0

    def remove_tariff_type_from_db(self, tariff_name):
        if self.check_associated_tariffs(tariff_name):
            return False
        else:
            query = "DELETE FROM tariffs WHERE name = %s AND type = %s"
            params = (tariff_name, True)
            self.execute_query(query, params)
            if not self.check_tariff_type_exists(tariff_name):
                logger.info("Removed tariff type: %s", tariff_name)
            return not self.check_tariff_type_exists(tariff_name)
