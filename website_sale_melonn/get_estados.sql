copy (
    select
        estado.id,
        estado.name,
        parent.name,
        pais.name
    from
        res_country_state estado
        join res_country pais on estado.country_id = pais.id
        join res_country_state parent on estado.parent_id = parent.id
    where
        pais.name = 'Colombia'
    order by
        estado.id
) to '/tmp/estados_dane.csv' header csv delimiter ',';
