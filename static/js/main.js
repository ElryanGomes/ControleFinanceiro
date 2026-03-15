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