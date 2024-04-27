import discord
from discord.ext import commands
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
import pandas as pd
import csv

# Configurando as intenções do bot
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True
intents.message_content = True

# Inicialização do bot
bot = commands.Bot(intents=intents, command_prefix='!')

@bot.event
async def on_ready():
    print(f'Funcionando como {bot.user}')

# Dicionários para guardar emails e códigos de verificação
user_email = {}
user_codes = {}

@bot.event
async def on_member_join(member):
    # Define o ID do canal de boas-vindas
    welcome_channel = bot.get_channel(1121155979938119790) # É necessário inserir o id do canal do seu servidor
    # Adiciona o cargo de pretendente (cargo que aguarda a autenticação) ao usuário
    new_member_role_id = 1117086568398733404 # É necessário inserir o id do cargo correspondente do seu servidor
    guild = member.guild
    role = guild.get_role(new_member_role_id)
    await member.add_roles(role)
    # Envia uma mensagem ao usuário solicitando o e-mail acadêmico
    await welcome_channel.send(f'{member.mention} Olá, informe o seu e-mail acadêmico.')

@bot.event
async def on_message(message):
    # Verifica se a mensagem é do próprio bot
    if message.author == bot.user:
        return

    # Verifica se a mensagem foi enviada no canal de autenticação
    if message.channel.id == 1121155979938119790: # É necessário inserir o id do canal de autenticação do seu servidor
        # Obtém o ID do usuário
        user_id = message.author.id
        # Carrega informações de alunos e professores a partir de arquivos CSV
        alunos = pd.read_csv(r"arquivo csv contendo informações dos alunos")
        professores = pd.read_csv(r"arquivo csv contendo informações dos professores")
        # Verifica se o usuario possui código de verificação pendente
        if user_id not in user_codes:
            email = message.content
            # Verifica se o email informado não faz parte da lista de alunos ou professores
            if email not in alunos['Nome da coluna com emails dos alunos'].values and email not in professores['Nome da coluna com emails dos professores'].values:
                # Se não fizer parte dos alunos ou professores vai ser banido
                await message.author.ban(reason='E-mail acadêmico não encontrado.')
                return
            # Se fizer parte da lista vai ser gerado um código de 6 digitos que será encaminhado para o email informado
            code = str(random.randint(1000000, 9999999))
            true_code = code[1:]
            # Armazena o código e o e-mail do usuário
            user_codes[user_id] = true_code
            user_email[user_id] = email

            enviar_email(email, true_code)
            await message.channel.send(f'{message.author.mention} Um código de verificação foi enviado para o seu email.\nDigite aqui neste chat apenas o código, se o código informado estiver errado ou demorar 5 minutos para digita-lo, você será removido!')
            # Define um timer para banir o usuário caso ele não digite o código em 5 minutos
            await banir_usuario(message, user_id)
        else:
            true_code = user_codes[user_id]
            # Verifica se o código digitado pelo usuário está correto
            if message.content == true_code:
                guild = message.guild
                # Verifica se o e-mail informado pelo usuário está associado a um aluno
                if user_email[user_id] in alunos['Nome da coluna com emails dos alunos'].values:
                    # Adiciona o cargo de aluno
                    aluno_role = 1117086721633419334 # É necessário inserir o id do cargo correspondente do seu servidor
                    role = guild.get_role(aluno_role)
                    await message.author.add_roles(role)
                    # Define o apelido do aluno no servidor
                    apelido = apelido_aluno(user_email[user_id])
                    await message.author.edit(nick=apelido)
                # Verifica se o e-mail informado pelo usuário está associado a um professor
                elif user_email[user_id] in professores['Nome da coluna com emails dos professores'].values:
                    # Adiciona o cargo de professor ao usuário
                    professor_role = 1117086500971106314 # É necessário inserir o id do cargo correspondente do seu servidor
                    role = guild.get_role(professor_role)
                    await message.author.add_roles(role)
                    # Define o apelido do professor no servidor
                    apelido = apelido_professor(user_email[user_id])
                    await message.author.edit(nick=apelido)
                # Remove o cargo de pretendente do usuário
                pretendente_role = 1117086568398733404 # É necessário inserir o id do cargo correspondente do seu servidor
                pretendente_remove = guild.get_role(pretendente_role)
                await message.author.remove_roles(pretendente_remove)
            # Se o código informado pelo usuario não estiver correto vai ser banido
            else:
                await message.author.ban(reason='Código de verificação incorreto!')
            # Após o processo de verificação remove os dados do usuario dos dicionários
            del user_codes[user_id]
            del user_email[user_id]
        # Processa outros comandos
        await bot.process_commands(message)

# Função para enviar o código de verificação por e-mail
def enviar_email(destinatario, code):
    # Define as configurações do servidor SMTP
    servidor_smtp = 'smtp.gmail.com'
    porta_smtp = 587
    remetente = 'email que irá enviar os códigos'
    senha = 'senha do email'
    # Cria o e-mail
    assunto = 'Código de verificação'
    corpo = 'O seu código de autenticação é: '
    corpo += code

    mensagem = MIMEMultipart()
    mensagem['From'] = remetente
    mensagem['To'] = destinatario
    mensagem['Subject'] = assunto
    mensagem.attach(MIMEText(corpo, 'plain'))
    # Conecta com o servidor SMTP
    servidor = smtplib.SMTP(servidor_smtp, porta_smtp)
    servidor.starttls()
    servidor.login(remetente, senha)
    # Envia um e-email contendo o código de verificação
    servidor.send_message(mensagem)
    # Fecha a conexão com o servidor SMTP
    servidor.quit()

# Função para banir o usuário caso ele não digite o código em 5 minutos
async def banir_usuario(message, user_id):
    # Define um timer de 300 segundos
    await asyncio.sleep(300)
    # Se o usuário não digitar o código quando o timer acabar o usuário vai ser banido 
    if user_id in user_codes:
        await message.author.ban(reason="Código de verificação não fornecido dentro do prazo.")
        del user_codes[user_id]

# Função para obter o nome completo do aluno a partir do e-mail
def apelido_aluno(email):
    # Abre o arquivo CSV com as informações dos alunos
    with open(r'arquivo csv contendo informações dos alunos') as arquivo:
        arquivo_aluno = csv.reader(arquivo)
        for linha in arquivo_aluno:
            if linha['Nome da coluna com emails dos alunos'] == email:
                return linha['Nome da coluna com nome completo dos alunos']
# Função para obter o nome completo do professor a partir do e-mail
def apelido_professor(email):
    with open(r'arquivo csv contendo informações dos professores') as arquivo:
        arquivo_professor = csv.reader(arquivo)
        for linha in arquivo_professor:
            if linha['Nome da coluna com emails dos professores'] == email:
                return linha['Nome da coluna com nome completo dos professores']

# Executa o bot
bot.run('Token do bot')