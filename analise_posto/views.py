from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncDate
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse
from usuarios.decorators import group_required
from postos.models import Posto
from vouchers.models import Voucher
from decimal import Decimal
from datetime import datetime
import logging
from .models import GastoVoucher
from .forms import RegistrarGastoForm

logger = logging.getLogger(__name__)

@login_required
@group_required('Gerente')
def analise_posto(request, posto_id):
    posto = get_object_or_404(Posto, id=posto_id)

    # Verificar se o usuário é o gerente do posto
    if request.user != posto.gerente:
        return render(request, 'erro_permissao.html')

    # Captura as datas de início e fim do filtro
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Filtra os gastos pela data, caso as datas estejam presentes
    gastos = GastoVoucher.objects.filter(posto=posto)
    if data_inicio:
        gastos = gastos.filter(data__gte=data_inicio)
    if data_fim:
        gastos = gastos.filter(data__lte=data_fim)

    # Agrupa os gastos por dia e calcula a soma
    gastos_agrupados = (
        gastos.annotate(dia=TruncDate('data'))
        .values('dia')
        .annotate(total_gasto=Sum('valor_gasto'))
        .order_by('dia')
    )

    # Extrai datas e valores para o gráfico
    data_vouchers = [gasto['dia'].strftime('%d/%m/%Y') for gasto in gastos_agrupados]
    valores_gastos = [float(gasto['total_gasto']) for gasto in gastos_agrupados]

    # Outros cálculos
    valor_total_utilizado = sum(valores_gastos)
    total_vouchers_usados = gastos.count()  # Contar registros de GastoVoucher

    context = {
        'posto': posto,
        'total_vouchers_usados': total_vouchers_usados,
        'valor_total_utilizado': valor_total_utilizado,
        'gastos': gastos,
        'data_inicio': data_inicio or '',
        'data_fim': data_fim or '',
        'data_vouchers': data_vouchers,  # Datas agrupadas
        'valores_gastos': valores_gastos,  # Valores somados
    }

    return render(request, 'analise_posto/analise_posto.html', context)

@login_required
@group_required('Gerente')
def listar_vouchers_posto(request, posto_id):
    posto = get_object_or_404(Posto, id=posto_id)
    
    # Verificar se o usuário é o gerente do posto
    if request.user != posto.gerente:
        return render(request, 'erro_permissao.html')

    vouchers = Voucher.objects.filter(rota__postos=posto, status='Ativo')

    context = {
        'posto': posto,
        'vouchers': vouchers,
    }
    
    return render(request, 'analise_posto/listar_vouchers_posto.html', context)

@login_required
@group_required('Gerente')
def registrar_gasto(request, voucher_id):
    voucher = get_object_or_404(Voucher, id=voucher_id)

    if request.method == 'POST':
        form = RegistrarGastoForm(request.POST)
        if form.is_valid():
            valor_gasto = form.cleaned_data['valor_gasto']
            request.session['valor_gasto'] = str(valor_gasto)  # Converte para string antes de salvar na sessão
            request.session['voucher_codigo'] = voucher.codigo  # Salva o código do voucher na sessão
            return redirect('escanear_voucher', voucher_id=voucher.id)
    else:
        form = RegistrarGastoForm()
    
    return render(request, 'analise_posto/registrar_gasto.html', {'form': form, 'voucher': voucher})

@login_required
@group_required('Gerente')
def escanear_voucher(request, voucher_id):
    voucher = get_object_or_404(Voucher, id=voucher_id)
    valor_gasto = request.session.get('valor_gasto')
    voucher_codigo = request.session.get('voucher_codigo')

    if valor_gasto is not None:
        valor_gasto = Decimal(valor_gasto)  # Converte de volta para Decimal

    return render(request, 'analise_posto/escanear_voucher.html', {'voucher': voucher, 'valor_gasto': valor_gasto})

@login_required
@group_required('Gerente')
def validar_qrcode(request, qrcode):
    voucher = get_object_or_404(Voucher, codigo=qrcode)
    valor_gasto = request.session.get('valor_gasto')
    voucher_codigo = request.session.get('voucher_codigo')
    gerente = request.user

    if valor_gasto is not None:
        valor_gasto = Decimal(valor_gasto)

    # Verificar se o gerente é responsável pelo posto específico
    postos_gerente = Posto.objects.filter(gerente=gerente)
    if not postos_gerente.exists():
        return JsonResponse({'status': 'error', 'message': 'Você não tem permissão para validar vouchers neste posto.'})

    logger.info(f"Validando QR Code: Voucher Código = {voucher.codigo}, Status = {voucher.status}, Valor Restante = {voucher.valor_restante}, Valor Gasto = {valor_gasto}")

    if voucher.codigo == voucher_codigo and voucher.status == 'Ativo' and voucher.valor_restante >= valor_gasto:
        voucher.valor_restante -= valor_gasto
        if voucher.valor_restante == 0:
            voucher.status = 'Usado'
        voucher.save(update_fields=['valor_restante', 'status'])
        
        # Registrar o gasto no posto
        for posto in postos_gerente:
            GastoVoucher.objects.create(voucher=voucher, posto=posto, valor_gasto=valor_gasto)

        voucher.refresh_from_db()
        logger.info(f"Voucher atualizado: Novo Valor Restante = {voucher.valor_restante}, Novo Status = {voucher.status}")
        return JsonResponse({'status': 'success', 'message': 'Voucher validado com sucesso!'})
    else:
        logger.error(f"Erro na validação do QR Code: QR Code inválido ou valor excede o restante do voucher.")
        return JsonResponse({'status': 'error', 'message': 'QR Code inválido ou valor excede o restante do voucher.'})