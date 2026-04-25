"""Registra el viaje a Guadalajara con sus gastos.

Uso:
    python seed_guadalajara.py
"""
from app import app, db, Trip, Expense

GUADALAJARA_EXPENSES = [
    ('uber dpaul', 40),
    ('dpaul', 2000),
    ('uber dpaul', 90),
    ('desayuno', 1209),
    ('oxxo', 200),
    ('uber de aeropuerto', 550),
    ('pan', 175),
    ('cena', 1337),
    ('carls jr', 430),
    ('hospedaje', 8000),
    ('vuelo', 5000),
]


def seed():
    with app.app_context():
        trip = Trip(destination='Guadalajara')
        db.session.add(trip)
        db.session.flush()
        for description, amount in GUADALAJARA_EXPENSES:
            db.session.add(Expense(
                trip_id=trip.id,
                description=description,
                amount=amount,
            ))
        db.session.commit()
        print(f'Viaje #{trip.id} a {trip.destination} registrado.')
        print(f'Gastos: {len(trip.expenses)}')
        print(f'Total: {trip.total()}')


if __name__ == '__main__':
    seed()
