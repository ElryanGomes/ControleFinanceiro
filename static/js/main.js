// Exemplo de como salvar um item
document.getElementById('salvarItem').addEventListener('click', () => {
    const item = {
        descricao: document.getElementById('nomeItem').value,
        valor: parseFloat(document.getElementById('valorItem').value),
        possuido: parseFloat(document.getElementById('valorPossuido').value),
        tipo: document.getElementById('tipoItem').value,
        situacao: "Pendente"
    };

    console.log("Salvando item:", item);
    // Aqui faremos a lógica de salvar no array e atualizar a tabela
    alert("Item adicionado com sucesso!");
});

 function abrirDetalhes(id) {
            document.getElementById('modal-' + id).style.display = 'flex';
        }

        function fecharDetalhes(id) {
            document.getElementById('modal-' + id).style.display = 'none';
        }

        // Fechar se clicar fora do card
        window.onclick = function (event) {
            if (event.target.className === 'detalhe-overlay') {
                event.target.style.display = 'none';
            }
        }