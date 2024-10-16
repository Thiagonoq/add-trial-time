import logging
from pymongo import MongoClient
from datetime import datetime, timedelta
import sys
import re
import asyncio

import config
from utils import log_config, inquirerpy
from src.database.mongo import mongo

DEV_MODE = config.DEV_MODE

PHONE_NUMBERS_DEV = [
    "+55 21 7506-8348"
]

NEW_TRIAL_TIME_DEV = 6


def add_time(actual_prospector, phone_numbers, mongo_config):
    loop = asyncio.get_event_loop()

    logging.info(phone_numbers)
    
    for phone_number in phone_numbers:
        phone = re.sub("\D", "", phone_number)

        try:
            trial_client = loop.run_until_complete(mongo.find_one("clients", {"client": phone}))
            
            if verify_client(trial_client, phone_number):
                continue

            client_name = trial_client.get('info', {}).get('name', '')

            client_add_trial_mongo_data = loop.run_until_complete(mongo.find_one("add_free_trial", {"client": phone}))
            if client_add_trial_mongo_data:
                trial_info = client_add_trial_mongo_data.get('trial_info', [])
                if trial_info:
                    input_response = "Sim"
                    last_trial_entry = trial_info[-1]
                    last_trial = last_trial_entry.get('added_date')
                    last_trial_by = last_trial_entry.get('added_by', 'N/A')

                    logging.info(
                        f"Cliente {client_name} já ganhou o trial dia {last_trial.strftime('%d/%m/%Y')}, adicionado por {last_trial_by}."
                    )
                    input_response = inquirerpy.ask_list("Deseja atualizar novamente?", ["Sim", "Não"])

                    if input_response == "Não":
                        logging.info('Trial não atualizado')
                        continue
            
            trial_time = mongo_config.get("trial_time", 6)
            if DEV_MODE:
                new_trial_time = NEW_TRIAL_TIME_DEV

            else:
                new_trial_time = inquirerpy.ask_number(f"Favor informe o tempo de trial de {phone_number} (em dias):", min=1)

            delta_days = (new_trial_time - trial_time)
            
            new_trial_date = datetime.now() + timedelta(days=delta_days)

            query = {"client": phone}
            update = {"$set": {"purchase.start_trial": new_trial_date, "purchase.use_limit": 50}}
            loop.run_until_complete(mongo.update_one("clients", query, update))

            logging.info(
                f"Trial do cliente {client_name} atualizado para {(new_trial_date + timedelta(days=7)).strftime('%d/%m/%Y')}"
            )

            new_trial_entry = {
                "added_date": datetime.now(),
                "added_by": actual_prospector
            }
            if client_add_trial_mongo_data:
                loop.run_until_complete(
                    mongo.update_one(
                        "add_free_trial", 
                        {"client": phone}, 
                        {"$push": {"trial_info": new_trial_entry}}    
                    )
                )

            else:
                loop.run_until_complete(
                    mongo.insert_one(
                        "add_free_trial", 
                        {
                            "client": phone,
                            "trial_info": [new_trial_entry]
                        }
                    )
                )
            
        except Exception as e:
            logging.error("Erro ao atualizar trial: %s", e)
        
def login(allowed_prospectors):
    trys = 0
    max_trys = 3
    access = False

    actual_prospector = inquirerpy.ask_list("Favor informe o usuário:", sorted(allowed_prospectors.keys()))
    while not access:
        try:
            password = inquirerpy.ask_password("Por favor, informe a senha:")

            if not password.isdigit():
                logging.info("A senha deve ser numérica. Tente novamente.")
                trys += 1
                if trys >= max_trys:
                    logging.info("Total de tentativas excedidas.")
                    input("Pressione ENTER para sair")
                    sys.exit(1)

                continue

            if int(password) != allowed_prospectors[actual_prospector]:
                logging.info("A senha digitada é inválida, tente novamente")
                trys += 1

                if trys >= max_trys:
                    logging.info("Total de tentativas excedidas.")
                    input("Pressione ENTER para sair")
                    sys.exit(1)
                    
                continue

            else:
                access = True

                logging.info(f"Cliente {actual_prospector} acessado")

        except Exception as e:
            logging.error("Erro ao logar: %s", e)
            trys += 1

            if trys >= max_trys:
                logging.info("Total de tentativas excedidas.")
                input("Pressione ENTER para sair")
                sys.exit(1)

    if not access:
        logging.error("Acesso não autorizado.")
        input("Pressione ENTER para sair")
        sys.exit(1)

    return actual_prospector

def get_phones(PHONE_NUMBERS_DEV):
    if DEV_MODE:
        phone_numbers = PHONE_NUMBERS_DEV

    else:
        has_number = True
        phone_numbers = []

        while has_number:
            try:
                phone_number_response = inquirerpy.ask_text("Por favor, digite o telefone que deseja atualizar o trial. (Deixe em branco para encerrar)")
                
                if phone_number_response == "":
                    break

                if phone_number_response in phone_numbers:
                    logging.warning("Telefone já informado")
                    continue
                
                if len(phone_number_response) < 12:
                    logging.warning("Telefone inválido. Por favor, informe um telefone correto")
                    continue

                phone_numbers.append(phone_number_response)
            
            except Exception as e:
                logging.error("Erro ao obter telefones: %s", e)

    return phone_numbers

def verify_client(trial_client, phone):
    if trial_client is None:
        logging.info(f"Cliente {phone} não encontrado")
        return True

    if trial_client.get('purchase', {}).get('type', '') == "paid":
        logging.info(f"Cliente {phone} já assina. Não precisa de trial")
        return True

    return False

def main():
    log_config.setup_logging()

    loop = asyncio.get_event_loop()

    try:
        mongo_config = loop.run_until_complete(mongo.find_one("config", {}))
        if not DEV_MODE:
            sellers = loop.run_until_complete(mongo.find("sellers", {}))
            allowed_prospectors = {prospector["name"].replace(" - Video AI", ""): prospector["id"] for prospector in sellers}
            actual_prospector = login(allowed_prospectors)

        else:
            actual_prospector = "Developer"
                    
        phone_numbers = get_phones(PHONE_NUMBERS_DEV)

        if len(phone_numbers) == 0:
            logging.warning("Nenhum telefone fornecido")
            return
        
        add_time(actual_prospector, phone_numbers, mongo_config)

    except Exception as e:
        logging.critical("Ocorreu um erro crítico: %s", e)
    
    finally:
        loop.close()
        logging.info("Conexão encerrada")
        input("Pressione ENTER para sair")

if __name__ == "__main__":
    main()