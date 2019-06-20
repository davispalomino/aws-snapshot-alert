quickstart: iniciar
	@echo "Deploy Finalizado"
iniciar:
	cd terraform/ && \
	terraform init
deploy:
	terraform plan