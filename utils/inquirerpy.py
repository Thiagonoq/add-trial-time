from InquirerPy import prompt
from InquirerPy.validator import PathValidator, EmptyInputValidator
from pathlib import Path
import os
import logging

from utils import log_config

log_config.setup_logging()

def ask_password(message):
    """
    Ask for a password
    :param message: Message to show
    :return: Password
    """
    questions = [
        {
            'type': 'password',
            'name': 'key_password',
            'message': message,
        }
    ]

    answers = prompt(questions)
    logging.info("Password informado.")
    
    return answers['key_password']

def ask_path(message, is_dir=False):
    """
    Ask for a path
    :param message: Message to show
    :param is_dir: If the path is a directory
    :return: Path
    """
    questions = [
        {
            'type': 'filepath',
            'message': message,
            'validate': PathValidator(is_dir=is_dir, message=f'{"Pasta" if is_dir else "Arquivo"} inexistente. Tente novamente.'),
            'name': 'path',
            'only_directories': is_dir,
            'only_files': not is_dir,
            'default': os.getcwd()
        }
    ]

    answers = prompt(questions)
    logging.info(f"Caminho informado: {answers['path']}")
     
    return Path(answers['path'])

def ask_list(message, choices):
    """
    Give a list of choices
    :param message: Message to show
    :param choices: List of choices
    :return: Choice
    """
    questions = [
        {
            'type': 'list',
            'message': message,
            'choices': choices,
            'name': 'choice'
        }
    ]

    answers = prompt(questions)
    logging.info(f"Opção informada: {answers['choice']}")
    return answers['choice']

def ask_text(message):
    """
    Ask for text
    :param message: Message to show
    :return: Text
    """
    questions = [
        {
            'type': 'input',
            'message': message,
            'name': 'text'
        }
    ]

    answers = prompt(questions)
    logging.info(f"Texto informado: {answers['text']}")
    return answers['text']

def ask_confirm(message):
    """
    Ask for confirmation
    :param message: Message to show
    :return: Confirmation
    """
    questions = [
        {
            'type': 'confirm',
            'message': message,
            'name': 'confirmation',
            'default': False
        }
    ]

    answers = prompt(questions)
    logging.info(f"Confirmação informada: {answers['confirmation']}")
    return answers['confirmation']

def ask_number(message, min):
    """
    Ask for a number
    :param message: Message to show
    :param min: Min number
    :param max: Max number
    :return: Number
    """
    questions = [
        {
            'type': 'number',
            'message': message,
            'name': 'number',
            'min_allowed': min,
            'default': None,
            'validate': EmptyInputValidator(message="Entrada inválida. Por favor, informe um número inteiro positivo."),
        }
    ]

    answers = prompt(questions)
    logging.info(f"Número informado: {answers['number']}")
    return int(answers['number'])