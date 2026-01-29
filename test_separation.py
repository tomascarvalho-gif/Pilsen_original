#!/usr/bin/env python3
"""
Script de teste rápido para verificar a separação downloader/visualizer

Testa:
1. Importação dos módulos
2. Estrutura de arquivos
3. Funções principais
"""

import os
import sys

def test_imports():
    """Testa se todos os módulos podem ser importados."""
    print("🧪 Teste 1: Importações...")
    try:
        import downloader
        print("  ✅ downloader.py importado com sucesso")
    except Exception as e:
        print(f"  ❌ Erro ao importar downloader: {e}")
        return False
    
    try:
        import visualizer
        print("  ✅ visualizer.py importado com sucesso")
    except Exception as e:
        print(f"  ❌ Erro ao importar visualizer: {e}")
        return False
    
    try:
        import info_picker_2
        print("  ✅ info_picker_2.py importado com sucesso")
    except Exception as e:
        print(f"  ❌ Erro ao importar info_picker_2: {e}")
        return False
    
    try:
        import helper
        print("  ✅ helper.py importado com sucesso")
    except Exception as e:
        print(f"  ❌ Erro ao importar helper: {e}")
        return False
    
    try:
        import indicators
        print("  ✅ indicators.py importado com sucesso")
    except Exception as e:
        print(f"  ❌ Erro ao importar indicators: {e}")
        return False
    
    return True


def test_file_structure():
    """Verifica se os arquivos principais existem."""
    print("\n🧪 Teste 2: Estrutura de arquivos...")
    
    required_files = [
        'downloader.py',
        'visualizer.py',
        'info_picker_2.py',
        'helper.py',
        'indicators.py',
        'requirements.txt'
    ]
    
    all_ok = True
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file} existe")
        else:
            print(f"  ❌ {file} NÃO encontrado")
            all_ok = False
    
    return all_ok


def test_downloader_functions():
    """Testa se as funções do downloader existem."""
    print("\n🧪 Teste 3: Funções do downloader...")
    
    try:
        import downloader
        
        functions = [
            'setup_sec_identity',
            'update_companies',
            'load_companies',
            'download_company_data',
            'download_all_companies',
            'verify_downloads'
        ]
        
        all_ok = True
        for func_name in functions:
            if hasattr(downloader, func_name):
                print(f"  ✅ {func_name}() encontrada")
            else:
                print(f"  ❌ {func_name}() NÃO encontrada")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f"  ❌ Erro ao verificar funções: {e}")
        return False


def test_visualizer_modifications():
    """Verifica se o visualizer foi modificado corretamente."""
    print("\n🧪 Teste 4: Modificações do visualizer...")
    
    try:
        with open('visualizer.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que NÃO tem mais as chamadas problemáticas
        checks = {
            'set_identity não deve estar no visualizer': 'set_identity(' not in content,
            'update_company_list não deve estar no visualizer': 'update_company_list(' not in content,
            'SecTools_export_important_data removido do loop': 'SecTools_export_important_data' not in content.split('def generate_graph')[1].split('def filter_summary_table')[0],
        }
        
        all_ok = True
        for check_name, result in checks.items():
            if result:
                print(f"  ✅ {check_name}")
            else:
                print(f"  ❌ {check_name}")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f"  ❌ Erro ao verificar modificações: {e}")
        return False


def test_data_directory():
    """Verifica se os diretórios de dados existem ou podem ser criados."""
    print("\n🧪 Teste 5: Diretórios de dados...")
    
    directories = ['xbrl_data_json']
    
    for directory in directories:
        if os.path.exists(directory):
            json_count = 0
            try:
                for ticker_folder in os.listdir(directory):
                    folder_path = os.path.join(directory, ticker_folder)
                    if os.path.isdir(folder_path):
                        json_count += len([f for f in os.listdir(folder_path) if f.endswith('.json')])
            except:
                pass
            
            if json_count > 0:
                print(f"  ✅ {directory}/ existe com {json_count} arquivos JSON")
            else:
                print(f"  ⚠️  {directory}/ existe mas está vazio (execute downloader.py)")
        else:
            print(f"  ⚠️  {directory}/ não existe (será criado ao executar downloader.py)")
    
    return True


def main():
    """Executa todos os testes."""
    print("="*80)
    print("TESTE DE SEPARAÇÃO DOWNLOADER/VISUALIZER")
    print("="*80 + "\n")
    
    results = []
    
    # Executar testes
    results.append(("Importações", test_imports()))
    results.append(("Estrutura de arquivos", test_file_structure()))
    results.append(("Funções do downloader", test_downloader_functions()))
    results.append(("Modificações do visualizer", test_visualizer_modifications()))
    results.append(("Diretórios de dados", test_data_directory()))
    
    # Resumo
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*80)
    print(f"RESULTADO: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 SUCESSO! Separação implementada corretamente!")
        print("\nPróximos passos:")
        print("1. python downloader.py --limit 5  # Testar download")
        print("2. python visualizer.py             # Testar visualização")
    else:
        print("⚠️  Alguns testes falharam. Revise os erros acima.")
    
    print("="*80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
