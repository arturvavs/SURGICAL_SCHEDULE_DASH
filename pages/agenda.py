import os
import pandas as pd
import oracledb as odb
import dash
import plotly.express as px
from sqlalchemy import create_engine
from dash import dcc, html, dash_table, Input, Output, callback, State
from datetime import datetime, timedelta
from sql_p import sql
from database import get_data
import duckdb
dash.register_page(__name__, path='/agenda',name='Agenda Diaria')


def criar_grafico(cirurgias_df, data_selecionada):
    if cirurgias_df.empty:
        return px.scatter(title="Sem agendamentos para esta data")
    
    cirurgias_df['status_formatado'] = cirurgias_df['status_sala'].apply(lambda x: ' ' if x == 'Livre' else 'Ocupado')
    
    # Verificar se a data selecionada é hoje
    hoje = datetime.now().strftime('%Y-%m-%d')
    hora_atual = datetime.now()
    
    # Mapa de cores estilo São Camilo (mais suave e profissional)
    color_map = {
        'Livre': '#96f296',  
        'Ocupado': '#f26d1f', 
        'Reservado': '#504eb5', 
        'Falta Justificada': '#d374f2',
        'Período sem agendamento': '#d9d9d9'  # Cor para horários passados (cinza claro)
    }

    # Determinar o intervalo de tempo para o eixo X
    date_obj = datetime.strptime(data_selecionada, '%Y-%m-%d')
    start_time = pd.to_datetime(data_selecionada + ' 04:00:00')
    end_time = pd.to_datetime(data_selecionada + ' 23:30:00')
    
    if not cirurgias_df.empty:
        min_time = min(cirurgias_df['hr_inicio'])
        if min_time < start_time:
            start_time = min_time
    
    # Criar uma cópia do DataFrame para não modificar o original
    df_completo = cirurgias_df.copy()
    
    # Se a data selecionada for hoje, criar registros para horários
    if data_selecionada <= hoje:
        # Converter hora_atual para o formato Timestamp para comparação
        hora_atual_ts = pd.Timestamp(hora_atual)
        
        # Obter todas as salas únicas
        salas = cirurgias_df['ds_agenda'].unique()
        
        # Para cada sala, verificar horários e adicionar registros
        for sala in salas:
            # Filtrar apenas os registros desta sala
            sala_df = cirurgias_df[cirurgias_df['ds_agenda'] == sala]
            
            # Ordenar os registros por horário de início
            sala_df = sala_df.sort_values('hr_inicio')
            
            # Horário de início do dia
            ultimo_horario = start_time
            
            # Lista para armazenar intervalos a serem adicionados
            novos_intervalos = []
            
            # Processar cada agendamento na sala
            for _, row in sala_df.iterrows():
                inicio = row['hr_inicio']
                fim = row['hr_fim']
                
                # Caso 1: Lacuna entre o último horário e o início do próximo agendamento
                if ultimo_horario < inicio:
                    # Se todo o intervalo é passado (antes da hora atual)
                    if inicio <= hora_atual_ts:
                        novos_intervalos.append({
                            'hr_inicio': ultimo_horario,
                            'hr_fim': inicio,
                            'ds_agenda': sala,
                            'status_sala': 'Período sem agendamento',
                            'nm_paciente': ' ',
                            'hr_inicio_fmt': ultimo_horario.strftime('%H:%M'),
                            'hr_fim_fmt': inicio.strftime('%H:%M'),
                            'ds_proc_interno': '',
                            'ds_tempo_total': '',
                            'nm_medico': '',
                            'ds_observacao': ' '
                        })
                    # Se o intervalo começa antes da hora atual mas termina depois
                    elif ultimo_horario < hora_atual_ts < inicio:
                        # Adicionar parte que já passou
                        novos_intervalos.append({
                            'hr_inicio': ultimo_horario,
                            'hr_fim': hora_atual_ts,
                            'ds_agenda': sala,
                            'status_sala': 'Período sem agendamento',
                            'nm_paciente': ' ',
                            'hr_inicio_fmt': ultimo_horario.strftime('%H:%M'),
                            'hr_fim_fmt': hora_atual_ts.strftime('%H:%M'),
                            'ds_proc_interno': '',
                            'ds_tempo_total': '',
                            'nm_medico': '',
                            'ds_observacao': ' '
                        })
                        # Adicionar parte livre entre hora atual e próximo agendamento
                        novos_intervalos.append({
                            'hr_inicio': hora_atual_ts,
                            'hr_fim': inicio,
                            'ds_agenda': sala,
                            'status_sala': 'Livre',
                            'nm_paciente': ' ',
                            'hr_inicio_fmt': hora_atual_ts.strftime('%H:%M'),
                            'hr_fim_fmt': inicio.strftime('%H:%M'),
                            'ds_proc_interno': '',
                            'ds_tempo_total': '',
                            'nm_medico': '',
                            'ds_observacao': ' '
                        })
                
                # Atualizar o último horário processado
                ultimo_horario = max(ultimo_horario, fim)
            
            # Verificar se há um intervalo entre o último agendamento e o fim do dia
            if ultimo_horario < end_time:
                # Se o último horário é anterior à hora atual
                if ultimo_horario < hora_atual_ts:
                    # Adicionar parte que já passou
                    novos_intervalos.append({
                        'hr_inicio': ultimo_horario,
                        'hr_fim': hora_atual_ts if hora_atual_ts < end_time else end_time,
                        'ds_agenda': sala,
                        'status_sala': 'Período sem agendamento',
                        'nm_paciente': ' ',
                        'hr_inicio_fmt': ultimo_horario.strftime('%H:%M'),
                        'hr_fim_fmt': (hora_atual_ts if hora_atual_ts < end_time else end_time).strftime('%H:%M'),
                        'ds_proc_interno': '',
                        'ds_tempo_total': '',
                        'nm_medico': '',
                        'ds_observacao': ' '
                    })
                    
                    # Se a hora atual ainda está dentro do horário de funcionamento
                    if hora_atual_ts < end_time:
                        # Adicionar horário livre do momento atual até o fim do dia
                        novos_intervalos.append({
                            'hr_inicio': hora_atual_ts,
                            'hr_fim': end_time,
                            'ds_agenda': sala,
                            'status_sala': 'Livre',
                            'nm_paciente': ' ',
                            'hr_inicio_fmt': hora_atual_ts.strftime('%H:%M'),
                            'hr_fim_fmt': end_time.strftime('%H:%M'),
                            'ds_proc_interno': '',
                            'ds_tempo_total': '',
                            'nm_medico': '',
                            'ds_observacao': ' '
                        })
                else:
                    # Todo o intervalo é futuro
                    novos_intervalos.append({
                        'hr_inicio': ultimo_horario,
                        'hr_fim': end_time,
                        'ds_agenda': sala,
                        'status_sala': 'Livre',
                        'nm_paciente': ' ',
                        'hr_inicio_fmt': ultimo_horario.strftime('%H:%M'),
                        'hr_fim_fmt': end_time.strftime('%H:%M'),
                        'ds_proc_interno': '',
                        'ds_tempo_total': '',
                        'nm_medico': '',
                        'ds_observacao': ' '
                    })
            
            # Adicionar todos os novos intervalos ao DataFrame principal
            for intervalo in novos_intervalos:
                df_completo = pd.concat([df_completo, pd.DataFrame([intervalo])], ignore_index=True)
    
    # Continuar com o código original, mas usando df_completo em vez de cirurgias_df
    fig = px.timeline(
        df_completo, 
        x_start='hr_inicio', 
        x_end='hr_fim', 
        y='ds_agenda',
        color='status_sala',
        color_discrete_map=color_map,
        custom_data=['nm_paciente', 'hr_inicio_fmt', 'hr_fim_fmt','ds_proc_interno','ds_tempo_total','nm_medico','ds_observacao'],
        labels={'ds_agenda': 'Sala'},
        height=800
    )

    
    # Determinar o intervalo de tempo para o eixo X
    date_obj = datetime.strptime(data_selecionada, '%Y-%m-%d')
    start_time = pd.to_datetime(data_selecionada + ' 04:00:00') #
    end_time = pd.to_datetime(data_selecionada + ' 23:30:00')
    
    
    if not cirurgias_df.empty:
        min_time = min(cirurgias_df['hr_inicio'])
        if min_time < start_time:
            start_time = min_time          
     
    fig.update_traces(
        textposition='auto', 
        marker=dict(
            line=dict(width=1.5, color='rgba(0, 0, 0, 0.3)'),
            opacity=0.9
        ),
        hovertemplate="<b>Sala: %{y}</b><br>" +
                    "<b>Paciente: %{customdata[0]}<br>" +
                    "<b>Início: %{customdata[1]}<br>" + 
                    "<b>Fim: %{customdata[2]}<br>" +
                    "<b>Procedimento: %{customdata[3]}<br>" +
                    "<b>Cirurgião: %{customdata[5]}<br>" +
                    "<b>Duração: %{customdata[4]}<br>"+
                    "<b>Obs: %{customdata[6]}<br>"
                    "<extra></extra>"
    )

    fig.update_layout(
        title=None,  # Removemos o título do gráfico para estilo São Camilo
        plot_bgcolor='#f8f9fa',
        paper_bgcolor='white',
        hovermode='closest',
        hoverlabel=dict(
            font_size=14,
            font_family='Arial',
            font_color='#333333',
            bordercolor='#dddddd',
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor='#e6e6e6',
            tickformat='%H:%M',
            title=None,  # Removido para design mais clean
            title_font={'size': 14},
        ),
        yaxis=dict(
            title=None,  # Removido para design mais clean
            title_font={'size': 16},
            categoryorder='category descending',
            tickfont=dict(size=14),
        ),
        margin=dict(l=50, r=30, t=20, b=50),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.05,
            xanchor='center',
            x=0.5,
            font=dict(color='black',size=16),
            title='',
            bgcolor='white',
            bordercolor='#e0e0e0',
            borderwidth=1
        ),
        dragmode=False,
        barmode='relative'
    )

    fig.update_xaxes(
        range=[start_time, end_time],
        tickformat='%H:%M',
        tickfont=dict(size=14),
        title=None,
        dtick=30 * 60 * 1000,  # Tick a cada 30 minutos (em milissegundos)
        showgrid=True,
        side='top',
        linecolor='#dddddd',
    )
    
    # Adiciona linhas verticais para cada hora para facilitar leitura
    for hour in range(4, 24):
        hour_time = pd.to_datetime(f"{data_selecionada} {hour:02d}:00:00")
        if start_time <= hour_time <= end_time:
            fig.add_shape(
                type="line",
                x0=hour_time,
                x1=hour_time,
                y0=-0.5,
                y1=len(cirurgias_df['ds_agenda'].unique()) - 0.5,
                line=dict(color="#e0e0e0", width=1),
                layer="below"
            )
    
    return fig

setor = ['UNA','UCB']

# Layout adaptado para estilo São Camilo
layout = html.Div([
    # Header com logo e título no estilo São Camilo
    html.Div([
        html.Img(src='/assets/logo_branca.png', className='logo'),
        html.H1('AGENDA CIRÚRGICA', className='titulo')
    ], className='header'),
    
    # Controles de data e setor - mantendo a estrutura lógica original
    html.Div([
        html.Div([
            html.Div([
                html.Label("Data:", style={'marginRight': 8, 'fontWeight': 'bold'}),
                dcc.DatePickerSingle(
                    id='date-picker',
                    date=datetime.now().strftime('%Y-%m-%d'),
                    display_format='DD/MM/YYYY',
                    style={'fontSize': 14},
                    clearable=False
                ),
            ], className='controle-item'),
            
            html.Div([
                html.Label("Setor:", style={'marginRight': 8, 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    ['UNA','UCB'],
                    'UNA',
                    id='dropdown-setor',
                    clearable=False,
                    style={'width':'120px'}
                )
            ], className='controle-item')
        ], className='controles')
    ], className='controles-wrapper'),
    
    # Container do gráfico
    html.Div([
        # Título da seção similar ao exemplo São Camilo
        html.H2("Cirurgias Agendadas", className='titulo-secao'),
        
        dcc.Loading(
            id="loading",
            type="circle",
            children=[
                dcc.Graph(
                    id='timeline-graph',
                    config={
                         'displayModeBar': False
                    },
                    style={'height': 'calc(100vh - 220px)'}
                )
            ]
        )
    ], className='grafico-container'),
    
    # Armazenar a data atual como um store para comparação (mantida lógica original)
    dcc.Store(id='current-date-store', data=datetime.now().strftime('%Y-%m-%d')),
    
    # Intervalo reduzido para verificar mudança de data mais frequentemente (a cada 30 segundos)
    dcc.Interval(
        id='interval-component',
        n_intervals=0,
        interval=120*1000
    )
], className='container')

# Callbacks originais mantidos sem alteração
@callback(
    Output('date-picker', 'date'),
    Output('current-date-store', 'data'),
    Input('interval-component', 'n_intervals'),
    State('date-picker', 'date'),
    State('current-date-store', 'data')
)
def update_date_at_midnight(n_intervals, current_picker_date, stored_date):
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    
    # Verifica se houve mudança de data desde a última verificação
    if today != stored_date:
        # Apenas atualiza se o usuário não tiver selecionado uma data manualmente
        # ou se a data atualmente selecionada for a do dia anterior
        if current_picker_date == stored_date:
            return today, today
    
    # Mantém a data atual do datepicker
    return current_picker_date, today

@callback(
    Output('timeline-graph', 'figure'),
    Input('dropdown-setor','value'),
    Input('interval-component','n_intervals'),
    Input('date-picker', 'date'),
)
def update_graph(ds_setor, n_intervals, date_value):
    if date_value is None:
        date_value = datetime.now().strftime('%Y-%m-%d')
    else:
        date_value = datetime.strptime(date_value.split('T')[0], '%Y-%m-%d').strftime('%Y-%m-%d')
    
    if ds_setor == 'UNA':
        cd_agenda = 209
    if ds_setor == 'UCB':
        cd_agenda = 210
    
    cirurgias = get_data(sql, date_value)
    cirurgia_setor = cirurgias.copy()
    cirurgia_setor = cirurgia_setor[cirurgia_setor['ds_setor']== ds_setor]
    return criar_grafico(cirurgia_setor, date_value)