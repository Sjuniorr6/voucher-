from django.shortcuts import render, redirect, get_object_or_404
from usuarios.decorators import group_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse  # Adicione esta linha
from .models import Voucher
from .forms import VoucherForm

@login_required
@group_required('Administrador','RMO')
def gerar_voucher(request):
    if request.method == 'POST':
        form = VoucherForm(request.POST)
        if form.is_valid():
            voucher = form.save(commit=False)
            voucher.valor_restante = 40  # Define o valor restante baseado na rota
            voucher.criado_por = request.user  # Define o usuário que criou o voucher
            voucher.save()
            return redirect('listar_vouchers')
    else:
        form = VoucherForm()
    return render(request, 'vouchers/gerar_voucher.html', {'form': form})

@login_required
@group_required('Administrador', 'PA', 'RMO')
def listar_vouchers(request):
    if request.user.groups.filter(name='PA').exists():  # Verifica se o usuário está no grupo PA
        vouchers = Voucher.objects.filter(status='Pendente')
    else:
        vouchers = Voucher.objects.all()
        for voucher in vouchers:
            if voucher.is_expired() and voucher.status != 'Expirado':
                voucher.status = 'Expirado'
                voucher.save()
    return render(request, 'vouchers/listar_vouchers.html', {'vouchers': vouchers})

@login_required
@group_required('PA')
def validar_voucher(request, codigo):
    try:
        # Validação do método HTTP
        if request.method != 'GET':
            return JsonResponse({'status': 'error', 'message': 'Método não permitido.'}, status=405)

        # Busca o voucher pelo código
        voucher = get_object_or_404(Voucher, codigo=codigo)

        # Verifica se o voucher está expirado
        if voucher.is_expired():
            if voucher.status != 'Expirado':
                voucher.status = 'Expirado'
                voucher.save()
            return JsonResponse({'status': 'error', 'message': 'O voucher expirou e não pode ser utilizado.'})

        # Verifica se o voucher já foi usado
        if voucher.status == 'Usado':
            return JsonResponse({'status': 'error', 'message': 'Este voucher já foi utilizado.'})

        # Atualiza o status do voucher
        if voucher.valor_restante > 0:
            voucher.status = 'Ativo'
        else:
            voucher.status = 'Usado'
        voucher.save()

        return JsonResponse({'status': 'success', 'message': 'Voucher validado com sucesso!'})

    except Voucher.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Voucher não encontrado.'}, status=404)
    except Exception as e:
        # Captura qualquer erro inesperado
        return JsonResponse({'status': 'error', 'message': f'Erro interno: {str(e)}'}, status=500)

@login_required
@group_required('PA')
def validar_qrcode_view(request):
    return render(request, 'vouchers/validar_voucher.html')