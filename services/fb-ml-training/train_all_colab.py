"""
FinBot - Setup e Treinamento de todos os 6 Modelos no Google Colab
=================================================================
Clona o repositório, instala dependências e roda o script unificado.
Pode ser executado em uma única célula do Colab:
  !wget -q https://raw.githubusercontent.com/FinBot-Crypto/fb-ml-training/main/train_all_colab.py
  %run train_all_colab.py
"""
import os
import subprocess
import sys

def run_cmd(cmd):
    print(f"Executando: {cmd}")
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in process.stdout:
        print(line, end='', flush=True)
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"Comando falhou com código {process.returncode}: {cmd}")

def main():
    # Verifica se está rodando no Google Colab
    if not os.path.exists('/content'):
        print("AVISO: Este script foi projetado para ser executado no Google Colab (/content).")
        print("Prosseguindo com a execução no diretório atual...")
        root_dir = os.getcwd()
    else:
        root_dir = '/content'
        os.chdir(root_dir)
        if os.path.exists('fb-ml-training'):
            print("Removendo clone antigo do repositório...")
            run_cmd('rm -rf fb-ml-training')
        
        print("Clonando o repositório fb-ml-training...")
        run_cmd('git clone https://github.com/FinBot-Crypto/fb-ml-training.git')
        os.chdir(os.path.join(root_dir, 'fb-ml-training'))
    
    print("Instalando dependências...")
    run_cmd('pip install -q -r requirements.txt')
    
    print("Iniciando o treinamento dos 6 modelos LSTM...")
    run_cmd('python -u _train_all_6_models.py')

if __name__ == "__main__":
    main()
