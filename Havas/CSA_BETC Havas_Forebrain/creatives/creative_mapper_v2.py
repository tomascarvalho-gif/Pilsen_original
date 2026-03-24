import pandas as pd
import io
import re

# --- DATA INPUT ---

spreadsheet_data = """
real_ad_name	Veículo	Campanha	Segmentação	Oferta	Criativo	Formato
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-custo-beneficio_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-custo-beneficio	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-gb-preco-v4_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-gb-preco-v4	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-gb-preco_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-gb-preco	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-hero-v2_27gb-38m_carrossel	facebook	asc	gross	27gb-38m	kv-hero-v2	carrossel
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-hero_27gb-38m_animado	facebook	asc	gross	27gb-38m	kv-hero	animado
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-hero_27gb-38m_carrossel	facebook	asc	gross	27gb-38m	kv-hero	carrossel
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-hero_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-hero	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-sem-surpresas_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-sem-surpresas	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-whats-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-whats-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-whats_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-whats	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-5g_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-5g	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-chip-gratis_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-chip-gratis	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-custo-beneficio-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-custo-beneficio-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-custo-beneficio_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-custo-beneficio	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-economia_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-economia	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-gb-preco-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-gb-preco-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-gb-preco-v3_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-gb-preco-v3	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-gb-preco_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-gb-preco	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-kv-hero_27gb-38m_animado	facebook	asc	gross	27gb-38m	pais-kv-hero	animado
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-kv-hero_27gb-38m_carrossel	facebook	asc	gross	27gb-38m	pais-kv-hero	carrossel
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-kv-hero_27gb-38m_catalogo	facebook	asc	gross	27gb-38m	pais-kv-hero	catalogo
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-ligacoes-ilimitadas-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-ligacoes-ilimitadas-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-ligacoes-ilimitadas_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-ligacoes-ilimitadas	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-sem-surpresas_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-sem-surpresas	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-whatsapp-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-whatsapp-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-whatsapp_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-whatsapp	estatico
tim-con_perene_conversao_pedido_socialads_esim_cpm_nacional_facebook_gross_custo-beneficio_27gb-38m_estatico	facebook	esim	gross	27gb-38m	custo-beneficio	estatico
tim-con_perene_conversao_pedido_socialads_esim_cpm_nacional_facebook_gross_esim-ativo_27gb-38m_estatico	facebook	esim	gross	27gb-38m	esim-ativo	estatico
tim-con_perene_conversao_pedido_socialads_esim_cpm_nacional_facebook_gross_gb-preco-v2_27gb-38m_estatico	facebook	esim	gross	27gb-38m	gb-preco-v2	estatico
tim-con_perene_conversao_pedido_socialads_esim_cpm_nacional_facebook_gross_gb-preco_27gb-38m_estatico	facebook	esim	gross	27gb-38m	gb-preco	estatico
tim-con_perene_conversao_pedido_socialads_esim_cpm_nacional_facebook_gross_kv-hero_27gb-38m_animado	facebook	esim	gross	27gb-38m	kv-hero	animado
tim-con_perene_conversao_pedido_socialads_esim_cpm_nacional_facebook_gross_kv-hero_27gb-38m_carrossel	facebook	esim	gross	27gb-38m	kv-hero	carrossel
tim-con_perene_conversao_pedido_socialads_esim_cpm_nacional_facebook_gross_kv-hero_27gb-38m_estatico	facebook	esim	gross	27gb-38m	kv-hero	estatico
tim-con_perene_conversao_pedido_socialads_esim_cpm_nacional_facebook_gross_ligacoes-ilimitadas_27gb-38m_estatico	facebook	esim	gross	27gb-38m	ligacoes-ilimitadas	estatico
tim-con_perene_conversao_pedido_socialads_migracao-premium_cpm_nacional_facebook_lake-tim_pais-custo-beneficio_45gb-64m_estatico	facebook	migracao-premium	lake-tim	45gb-64m	pais-custo-beneficio	estatico
tim-con_perene_conversao_pedido_socialads_migracao-premium_cpm_nacional_facebook_lake-tim_pais-gb-preco_45gb-64m_estatico	facebook	migracao-premium	lake-tim	45gb-64m	pais-gb-preco	estatico
tim-con_perene_conversao_pedido_socialads_migracao_cpm_nacional_facebook_base_pais-kv-hero_31gb-44m_animado	facebook	migracao	base	31gb-44m	pais-kv-hero	animado
tim-con_perene_conversao_pedido_socialads_portin-actionable_cpm_nacional_facebook_interesses-tim_kv-hero_27gb-38m_animado	facebook	portin-actionable	interesses-tim	27gb-38m	kv-hero	animado
tim-con_perene_conversao_pedido_socialads_portin-actionable_cpm_nacional_facebook_interesses-tim_kv-hero_27gb-38m_carrossel	facebook	portin-actionable	interesses-tim	27gb-38m	kv-hero	carrossel
tim-con_perene_conversao_pedido_socialads_portin-actionable_cpm_nacional_facebook_interesses-tim_kv-hero_27gb-38m_estatico	facebook	portin-actionable	interesses-tim	27gb-38m	kv-hero	estatico
tim-con_perene_conversao_pedido_socialads_remarketing-gross_cpm_nacional_facebook_gross_kv-hero_27gb-38m_animado	facebook	remarketing-gross	gross	27gb-38m	kv-hero	animado
tim-con_perene_conversao_pedido_socialads_remarketing-gross_cpm_nacional_facebook_gross_kv-hero_27gb-38m_carrossel	facebook	remarketing-gross	gross	27gb-38m	kv-hero	carrossel
tim-con_perene_conversao_pedido_socialads_remarketing-gross_cpm_nacional_facebook_gross_kv-hero_27gb-38m_estatico	facebook	remarketing-gross	gross	27gb-38m	kv-hero	estatico
tim-con_perene_conversao_pedido_socialads_remarketing-gross_cpm_nacional_facebook_gross_pais-kv-hero_27gb-38m_animado	facebook	remarketing-gross	gross	27gb-38m	pais-kv-hero	animado
tim-con_perene_conversao_pedido_socialads_remarketing-gross_cpm_nacional_facebook_gross_pais-kv-hero_27gb-38m_carrossel	facebook	remarketing-gross	gross	27gb-38m	pais-kv-hero	carrossel
tim-con_perene_conversao_pedido_socialads_remarketing-gross_cpm_nacional_facebook_gross_pais-kv-hero_27gb-38m_estatico	facebook	remarketing-gross	gross	27gb-38m	pais-kv-hero	estatico
tim-con_perene_conversao_pedido_socialads_remarketing-migracao_cpm_nacional_facebook_migracao_kv-hero-pais_31gb-44m_animado	facebook	remarketing-migracao	migracao	31gb-44m	kv-hero-pais	animado
tim-con_perene_conversao_pedido_socialads_remarketing-migracao_cpm_nacional_facebook_migracao_kv-hero-pais_31gb-44m_carrossel	facebook	remarketing-migracao	migracao	31gb-44m	kv-hero-pais	carrossel
tim-con_perene_conversao_pedido_socialads_remarketing-migracao_cpm_nacional_facebook_migracao_kv-hero-pais_31gb-44m_estatico	facebook	remarketing-migracao	migracao	31gb-44m	kv-hero-pais	estatico
tim-con_perene_conversao_pedido_socialads_remarketing-migracao_cpm_nacional_facebook_migracao_kv-hero_31gb-44m_animado	facebook	remarketing-migracao	migracao	31gb-44m	kv-hero	animado
tim-con_perene_conversao_pedido_socialads_remarketing-migracao_cpm_nacional_facebook_migracao_kv-hero_31gb-44m_carrossel	facebook	remarketing-migracao	migracao	31gb-44m	kv-hero	carrossel
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-gb-preco-v5_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-gb-preco-v5	estatico
tim-con_perene_conversao_pedido_socialads_migracao-premium_cpm_nacional_facebook_lake-tim_pais-chip-gratis_45gb-64m_estatico	facebook	migracao-premium	lake-tim	45gb-64m	pais-chip-gratis	estatico
tim-con_perene_conversao_pedido_socialads_migracao-premium_cpm_nacional_facebook_lake-tim_pais-redes-sociais_45gb-64m_estatico	facebook	migracao-premium	lake-tim	45gb-64m	pais-redes-sociais	estatico
tim-con_perene_conversao_pedido_socialads_migracao-premium_cpm_nacional_facebook_lake-tim_pais-sem-surpresas_45gb-64m_estatico	facebook	migracao-premium	lake-tim	45gb-64m	pais-sem-surpresas	estatico
tim-con_perene_conversao_pedido_socialads_migracao_cpm_nacional_facebook_base_pais-economia_31gb-44m_estatico	facebook	migracao	base	31gb-44m	pais-economia	estatico
tim-con_perene_conversao_pedido_socialads_migracao_cpm_nacional_facebook_base_pais-gb-preco_31gb-44m_estatico	facebook	migracao	base	31gb-44m	pais-gb-preco	estatico
tim-con_perene_conversao_pedido_socialads_migracao-premium_cpm_nacional_facebook_lake-tim_pais-choice-bundle_45gb-64m_estatico	facebook	migracao-premium	lake-tim	45gb-64m	pais-choice-bundle	estatico
tim-con_perene_conversao_pedido_socialads_migracao_cpm_nacional_facebook_base_pais-chip-gratis_31gb-44m_estatico	facebook	migracao	base	31gb-44m	pais-chip-gratis	estatico
tim-con_perene_conversao_pedido_socialads_migracao_cpm_nacional_facebook_base_pais-kv-hero_31gb-44m_estatico	facebook	migracao	base	31gb-44m	pais-kv-hero	estatico
tim-con_perene_conversao_pedido_socialads_migracao-premium_cpm_nacional_facebook_lake-tim_pais-kv-hero_45gb-64m_animado	facebook	migracao-premium	lake-tim	45gb-64m	pais-kv-hero	animado
tim-con_perene_conversao_pedido_socialads_migracao-premium_cpm_nacional_facebook_lake-tim_pais-kv-hero_45gb-64m_carrossel	facebook	migracao-premium	lake-tim	45gb-64m	pais-kv-hero	carrossel
tim-con_perene_conversao_pedido_socialads_migracao-premium_cpm_nacional_facebook_lake-tim_pais-kv-hero_45gb-64m_estatico	facebook	migracao-premium	lake-tim	45gb-64m	pais-kv-hero	estatico
tim-con_perene_conversao_pedido_socialads_migracao_cpm_nacional_facebook_base_pais-custo-beneficio_31gb-44m_estatico	facebook	migracao	base	31gb-44m	pais-custo-beneficio	estatico
tim-con_perene_conversao_pedido_socialads_migracao_cpm_nacional_facebook_base_pais-kv-hero_31gb-44m_carrossel	facebook	migracao	base	31gb-44m	pais-kv-hero	carrossel
tim-con_perene_conversao_pedido_socialads_migracao_cpm_nacional_facebook_base_pais-whatsapp_31gb-44m_estatico	facebook	migracao	base	31gb-44m	pais-whatsapp	estatico
tim-con_perene_conversao_pedido_socialads_remarketing-migracao_cpm_nacional_facebook_migracao_kv-hero_31gb-44m_estatico	facebook	remarketing-migracao	migracao	31gb-44m	kv-hero	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-kv-hero_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-kv-hero	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-sem-surpresas-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-sem-surpresas-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-gb-preco-v3_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-gb-preco-v3	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-chip-gratis_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-chip-gratis	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-5g_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-5g	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-5g-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-5g-v2	estatico
tim-con_perene_conversao_pedido_socialads_migracao_cpm_nacional_facebook_base_pais-ligacoes-ilimitadas_31gb-44m_estatico	facebook	migracao	base	31gb-44m	pais-ligacoes-ilimitadas	estatico
tim-con_perene_conversao_pedido_socialads_catalogo-v2_cpm_nacional_facebook_lake-tim_pais-kv-hero_31gb-44m_catalogo	facebook	catalogo-v2	lake-tim	31gb-44m	pais-kv-hero	catalogo
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_pais-chip-gratis-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	pais-chip-gratis-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-hero-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-hero-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-gb-preco-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-gb-preco-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-custo-beneficio-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-custo-beneficio-v2	estatico
tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-chip-gratis-v2_27gb-38m_estatico	facebook	asc	gross	27gb-38m	kv-chip-gratis-v2	estatico
"""

file_list = [
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ANIMADAS\GOOGLE\GOOGLE_1200x1200.mp4",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ANIMADAS\GOOGLE\GOOGLE_1200x628.mp4",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ANIMADAS\GOOGLE\GOOGLE_900x1200.mp4",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ANIMADAS\KWAI\KWAI_720x1080.mp4",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ANIMADAS\META\META_1080x1080.mp4",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ANIMADAS\META\META_1080x1920.mp4",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ANIMADAS\META\META_1920x1080.mp4",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ANIMADAS\TIKTOK\TIKTOK_540x960.mp4",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\BANNER\TIM_CONTROLE_PERFORMANCE_CONSID_FEV_HERO_BANNER_300X60.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\1200x1200\STEP 01.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\1200x1200\STEP 02.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\1200x1200\STEP 03.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\1200x1200\STEP 04.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\1200x628\STEP 01.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\1200x628\STEP 02.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\1200x628\STEP 03.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\1200x628\STEP 04.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\960x1200\STEP 01.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\960x1200\STEP 02.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\960x1200\STEP 03.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\CARROSSEL\960x1200\STEP 04.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA CONEXAO\LINHA 5G 1200x1200.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA CONEXAO\LINHA 5G 1200x628.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA CONEXAO\LINHA 5G 960x1200.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA CONEXAO\LINHA REDES 1200x1200.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA CONEXAO\LINHA REDES 1200x628.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA CONEXAO\LINHA REDES 960x1200.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA CONEXAO\LINHA WHATSAPP 1200x1200.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA CONEXAO\LINHA WHATSAPP 1200x628.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA CONEXAO\LINHA WHATSAPP 960x1200.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA STREAMING\CHOICE BUNDLE 1200x1200.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA STREAMING\CHOICE BUNDLE 1200x628.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\GOOGLE\DEMAND GEN\LINHA STREAMING\CHOICE BUNDLE 960x1200.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\LOGO\TIM_CONTROLE_PERFORMANCE_CONSID_FEV_LOGO_1200x1200.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\KV HERO\1080X1080.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\KV HERO\1080X1920.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\KV HERO\1920X1080.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA 5G\LINHA 5G 1080x1080.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA 5G\LINHA 5G 1080x1920.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA 5G\LINHA 5G 1920x1080.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA CHOICE BUNDLE (LOGO ATUALIZADA)\LINHA CHOICE BUNDLE 1080x1080.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA CHOICE BUNDLE (LOGO ATUALIZADA)\LINHA CHOICE BUNDLE 1080x1920.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA CHOICE BUNDLE (LOGO ATUALIZADA)\LINHA CHOICE BUNDLE 1920x1080.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA REDES\LINHA REDES 1080x1080.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA REDES\LINHA REDES 1080x1920.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA REDES\LINHA REDES 1920x1080.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA WHATSAPP\LINHA WHATSAPP 1080x1080.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA WHATSAPP\LINHA WHATSAPP 1080x1920.png",
    r"\ALWAYS ON (ENXOVAL DE SEMPRE)\ESTÁTICAS\META\LINHAS ALTERNATIVAS\LINHA WHATSAPP\LINHA WHATSAPP 1920x1080.png",
    r"\PERENES (27, 35 e 45GB)\ANIMADAS\27 GB\Facebook\27GB_FACEBOOK_1080x1080_15s.mp4",
    r"\PERENES (27, 35 e 45GB)\ANIMADAS\27 GB\Facebook\27GB_FACEBOOK_1080x1920_15s.mp4",
    r"\PERENES (27, 35 e 45GB)\ANIMADAS\27 GB\Facebook\27GB_FACEBOOK_1920x1080_15s.mp4",
    r"\PERENES (27, 35 e 45GB)\ANIMADAS\45 GB\META\45GB_FACEBOOK_1080x1080_15s.mp4",
    r"\PERENES (27, 35 e 45GB)\ANIMADAS\45 GB\META\45GB_FACEBOOK_1080x1920_15s.mp4",
    r"\PERENES (27, 35 e 45GB)\ANIMADAS\45 GB\META\45GB_FACEBOOK_1920x1080_15s.mp4",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\CARROSSEL\1080X1080\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_1080X1080_STEP 1.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\CARROSSEL\1080X1080\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_1080X1080_STEP 2.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\CARROSSEL\1080X1080\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_1080X1080_STEP 3.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\CARROSSEL\1080X1080\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_1080X1080_STEP 4.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\CARROSSEL\1080x1920\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_ANIMADAS_1080X1920_STEP 1.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\CARROSSEL\1080x1920\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_ANIMADAS_1080X1920_STEP 2.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\CARROSSEL\1080x1920\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_ANIMADAS_1080X1920_STEP 3.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\CARROSSEL\1080x1920\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_ANIMADAS_1080X1920_STEP 4.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\CATÁLOGO\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_CATÁLOGO_1080X1080_v2.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\PPL\KV HERO\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_PPL_1080X1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\PPL\KV HERO\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_PPL_1080X1920.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\PPL\KV HERO\TIM_CONTROLE_ABRIL_27GB_FACEBOOK_PPL_1920X1080.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\PPL\LINHAS ALTERNATIVAS\1080x1080\27GB_PPL_KVCHIPGRATIS_1080x1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\PPL\LINHAS ALTERNATIVAS\1080x1080\27GB_PPL_KVCHOICEBUNDLE_1080x1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\PPL\LINHAS ALTERNATIVAS\1080x1080\27GB_PPL_KVCONEXÃO_1080x1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\PPL\LINHAS ALTERNATIVAS\1080x1080\27GB_PPL_KVGBPREÇO_1080x1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\PPL\LINHAS ALTERNATIVAS\1080x1080\27GB_PPL_KVPLANOCOMPLETO_1080x1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\27GB\META\PPL\LINHAS ALTERNATIVAS\1080x1080\27GB_PPL_KVSEMSURPRESA_1080x1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\CARROSSEL\1080X1080\STEP_01.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\CARROSSEL\1080X1080\STEP_02.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\CARROSSEL\1080X1080\STEP_03.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\CARROSSEL\1080X1080\STEP_04.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\CARROSSEL\1080x1920\STEP_01.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\CARROSSEL\1080x1920\STEP_02.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\CARROSSEL\1080x1920\STEP_03.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\CARROSSEL\1080x1920\STEP_04.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\CATÁLOGO\TIM_CONTROLE_ABRIL_45GB_META_CATÁLOGO_1080X1080 V2.png",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\ESTÁTICAS\KV HERO\TIM_CONTROLE_ABRIL_45GB_FACEBOOK_PPL_1080X1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\ESTÁTICAS\KV HERO\TIM_CONTROLE_ABRIL_45GB_FACEBOOK_PPL_1080X1920.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\ESTÁTICAS\KV HERO\TIM_CONTROLE_ABRIL_45GB_FACEBOOK_PPL_1920X1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\ESTÁTICAS\LINHAS ALTERNATIVAS\1080x1080\45GB_PPL_KVCHIPGRATIS_1080x1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\ESTÁTICAS\LINHAS ALTERNATIVAS\1080x1080\45GB_PPL_KVCHOICEBUNDLE_1080x1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\ESTÁTICAS\LINHAS ALTERNATIVAS\1080x1080\45GB_PPL_KVGBPREÇO_1080x1080.jpg",
    r"\PERENES (27, 35 e 45GB)\ESTÁTICAS\45GB\FACEBOOK\ESTÁTICAS\LINHAS ALTERNATIVAS\1080x1080\45GB_PPL_KVSEMSURPRESA_1080x1080.jpg",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ANIMADAS\META\Meta_1080x1080.mp4",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ANIMADAS\META\Meta_1080x1920.mp4",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ANIMADAS\META\Meta_1920x1080.mp4",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\CARROSSEL\1080x1080\card 1.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\CARROSSEL\1080x1080\card 2.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\CARROSSEL\1080x1080\card 3.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\CARROSSEL\1080x1080\card 4.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\KV HERO\KV HERO QUAD.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\KV HERO\KV HERO VERT.jpg",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\KV HERO\KV HERO.jpg",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\LINHAS ALTERNATIVAS\1080x1080\01_GB E PREÇO.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\LINHAS ALTERNATIVAS\1080x1080\02_CHIP GRÁTIS.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\LINHAS ALTERNATIVAS\1080x1080\03_CONTA SEM SURPRESAS.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\LINHAS ALTERNATIVAS\1080x1080\04_CUSTO BENEFÍCIO.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\LINHAS ALTERNATIVAS\1080x1080\05_WHATSAPP INCLUÍDO.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\(NOVO MATERIAL) PORTABILIDADE 27GB POR R$38,99\1º IMPACTO\ESTATICAS\META\LINHAS ALTERNATIVAS\1080x1080\06_LÍDER EM 5G.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\GROSS 31GB por R$44,99\1º impacto\ANIMADAS\META\1080x1080_META_15s.mp4",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\GROSS 31GB por R$44,99\1º impacto\ANIMADAS\META\1080x1920_META_15s.mp4",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\GROSS 31GB por R$44,99\1º impacto\ANIMADAS\META\1920x1080_META_15s.mp4",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\GROSS 31GB por R$44,99\1º impacto\ESTÁTICAS\CARROSSEL\1080x1080\STEP 01.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\GROSS 31GB por R$44,99\1º impacto\ESTÁTICAS\CARROSSEL\1080x1080\STEP 02.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\GROSS 31GB por R$44,99\1º impacto\ESTÁTICAS\CARROSSEL\1080x1080\STEP 03.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\GROSS 31GB por R$44,99\1º impacto\ESTÁTICAS\KV HERO\META\1080x1080.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\GROSS 31GB por R$44,99\1º impacto\ESTÁTICAS\KV HERO\META\1080x1920.png",
    r"\Tim Controle Mes Agosto 25 Performance OFERTAS _BTL_\GROSS 31GB por R$44,99\1º impacto\ESTÁTICAS\KV HERO\META\1920x1080.png",
]
# Note: I have trimmed the file list to the most relevant examples for brevity in the code block.
# The logic will work on the full list provided in the prompt.

# --- DATA PROCESSING ---

# Load data into a pandas DataFrame
df = pd.read_csv(io.StringIO(spreadsheet_data), sep='\t')

def normalize_text(text):
    """Lowercase, remove accents, and replace separators with spaces."""
    if not isinstance(text, str):
        return ""
    # A simple way to handle common accents without extra libraries
    text = text.replace('á', 'a').replace('ã', 'a').replace('ç', 'c').replace('é', 'e').replace('ê', 'e')
    text = text.lower()
    text = re.sub(r'[-_\s]+', ' ', text) # Replace hyphens, underscores, and spaces with a single space
    return text.strip()

def get_keywords_from_row(row):
    """Extract and normalize keywords from a spreadsheet row."""
    keywords = set()
    
    # Offer (e.g., '27gb')
    oferta_match = re.search(r'(\d+gb)', row['Oferta'])
    if oferta_match:
        keywords.add(oferta_match.group(1))

    # Platform (handle synonyms)
    veiculo = normalize_text(row['Veículo'])
    if veiculo == 'facebook':
        keywords.add('meta')
        keywords.add('facebook')
    else:
        keywords.add(veiculo)
        
    # Format (handle synonyms)
    formato = normalize_text(row['Formato'])
    if formato == 'estatico':
        keywords.add('estaticas')
    elif formato == 'animado':
        keywords.add('animadas')
    else:
        keywords.add(formato) # e.g., 'carrossel', 'catalogo'
        
    # Creative (this is the most complex)
    # Remove common prefixes and split into words
    criativo = normalize_text(row['Criativo'])
    criativo = re.sub(r'^(kv|pais) ', '', criativo)
    criativo = re.sub(r' v\d$', '', criativo) # remove version numbers like v2, v3
    keywords.update(criativo.split())

    # Campaign Type
    keywords.add(normalize_text(row['Campanha']))

    return keywords

def score_file(filepath, keywords):
    """Score a filepath based on how many keywords it contains."""
    score = 0
    normalized_path = normalize_text(filepath)
    
    for keyword in keywords:
        if keyword in normalized_path:
            # Give higher weight to more specific keywords
            if 'gb' in keyword:
                score += 5 # Offer is very important
            elif keyword in ['estaticas', 'animadas', 'carrossel', 'catalogo']:
                score += 3 # Format is important
            else:
                score += 1
                
    return score

# --- MAIN LOGIC ---

results = {}
unmatched_count = 0

for index, row in df.iterrows():
    ad_name = row['real_ad_name']
    ad_keywords = get_keywords_from_row(row)
    
    scored_files = []
    for f in file_list:
        current_score = score_file(f, ad_keywords)
        if current_score > 0:
            scored_files.append({'file': f, 'score': current_score})
            
    if not scored_files:
        results[ad_name] = ["-- NO MATCH FOUND --"]
        unmatched_count += 1
        continue
        
    # Find the highest score
    max_score = max(f['score'] for f in scored_files)
    
    # Get all files that have the highest score
    best_matches = [f['file'] for f in scored_files if f['score'] == max_score]
    
    results[ad_name] = best_matches

# --- PRINT RESULTS ---

for ad_name, matches in results.items():
    print(f"Ad Name: {ad_name}")
    print("  -> Mapped File(s):")
    for match in matches:
        print(f"     - {match}")
    print("-" * 50)

print(f"\n--- SUMMARY ---")
print(f"Total Ads Processed: {len(df)}")
print(f"Ads with Matches: {len(df) - unmatched_count}")
print(f"Ads without Matches: {unmatched_count}")
