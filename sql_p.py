sql = """select 
to_char(a.hr_inicio,'dd/mm/yyyy')dt_agenda,
a.hr_inicio, 
--case when a.cd_pessoa_fisica is not null then a.nr_minuto_duracao||' minutos' else 'Livre' end as ds_tempo_total,
decode(a.nr_minuto_duracao,0,30,a.nr_minuto_duracao)||' minutos' ds_tempo_total,
(a.hr_inicio + (decode(a.nr_minuto_duracao,0,30,a.nr_minuto_duracao)/1440))hr_fim,
a.cd_agenda,
to_char(a.hr_inicio,'hh24:mi')hr_inicio_fmt,
to_char(((a.hr_inicio + (decode(a.nr_minuto_duracao,0,30,a.nr_minuto_duracao)/1440))),'hh24:mi')hr_fim_fmt,
decode(a.cd_agenda,212,1,309,2,317,3,318,4,320,5,321,6,322,7,323,8)cd_sala,
replace(replace(obter_desc_agenda(a.cd_agenda),'UNA - ',''),'UCB - ','') ds_agenda,
case when a.cd_pessoa_fisica is null then ' ' else obter_nome_pf(a.cd_pessoa_fisica) end nm_paciente,
--decode(obter_nome_pf(a.cd_pessoa_fisica),null,'',obter_nome_pf(a.cd_pessoa_fisica))nm_paciente,
case when a.nr_seq_proc_interno is null then ' ' else obter_desc_proc_interno(a.nr_seq_proc_interno) end ds_proc_interno,
case when a.cd_medico is null then ' ' else obter_nome_pf(a.cd_medico) end nm_medico,
a.nr_cirurgia,
case 
    when (a.ie_status_agenda = 'F') then 'Falta Justificada'
    when (a.cd_pessoa_fisica is not null and a.cd_medico is not null) then 'Ocupado' 
    when (a.cd_pessoa_fisica is null and a.cd_medico is not null and a.ie_status_agenda <> 'F') then 'Reservado'
    when (a.cd_pessoa_fisica is null and a.cd_medico is null) then 'Livre' end status_sala,

    --when ()
decode(obter_setor_agenda(a.cd_agenda),209,'UNA',210,'UCB')ds_Setor,
case when a.DS_OBSERVACAO is null then ' ' else a.ds_observacao end ds_observacao
from agenda_paciente a
where 1=1
and trunc(a.dt_agenda) = TO_DATE(:dt_inicio, 'YYYY-MM-DD')
and a.cd_motivo_cancelamento is null
--and obter_setor_agenda(a.cd_agenda) = :cd_agenda
--and a.cd_pessoa_fisica is not null
and a.cd_agenda in (212,309,317,318,320,321,322,323,310,314,312,315,316)
--and a.cd_agenda = 322
--and a.IE_STATUS_AGENDA not in ('F')

order by 5,a.hr_inicio asc
"""

