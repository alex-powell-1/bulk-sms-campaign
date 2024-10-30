import platform
from config_file import config_data


class Config:
    company: dict = config_data['company']
    sql: dict = config_data['sql']
    keys: dict = config_data['keys']
    integrator: dict = config_data['integrator']
    api: dict = config_data['api']


class SQL:
    """SQL Server Configuration"""

    SERVER: str = Config.sql['address']
    DATABASE: str = Config.sql['database']
    PORT: int = Config.sql['port']
    USERNAME: str = Config.sql['db_username']
    PASSWORD: str = Config.sql['db_password']


# Company
class Company:
    name = Config.company['name']
    logo = Config.company['logo']


class Table:
    """Tables for SQL Queries"""

    sms = Config.company['tables']['sms']
    sms_event = Config.company['tables']['sms_event']

    class CP:
        """Counterpoint Tables"""

        customers = config_data['counterpoint']['tables']['customers']

        class Customers:
            """Counterpoint Customer Table"""

            table = config_data['counterpoint']['tables']['customers']['table']

            class Column:
                __col = config_data['counterpoint']['tables']['customers']['columns']
                number = __col['number']
                first_name = __col['first_name']
                last_name = __col['last_name']
                mobile_phone_1: str = __col['mobile_phone_1']
                mobile_phone_2 = __col['mobile_phone_2']
                sms_1_is_subscribed = __col['sms_1_is_subscribed']
                sms_2_is_subscribed = __col['sms_2_is_subscribed']


class Twilio:
    phone_number = Config.keys['twilio']['twilio_phone_number']
    sid = Config.keys['twilio']['twilio_account_sid']
    token = Config.keys['twilio']['twilio_auth_token']


class API:
    server_name: str = Config.api['server_name']


class Integrator:
    """Integrator Configuration"""

    # Local Development
    if platform.system() == 'Windows':
        logs = f'//{API.server_name}/' + Config.integrator['logs']
    else:
        logs = '/Volumes/' + Config.integrator['logs']


class Logs:
    sms = f'{Integrator.logs}/sms'
    sms_events = f'{Integrator.logs}/sms'
