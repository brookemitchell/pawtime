:- dynamic scheduled/3.

vet(sri).
vet(saurabh).
vet(krishan).
tech(brooke).
tech(dave).
tech(duncan).
base_price(consultation, 50).
base_price(surgery, 200).

slot(9).
slot(10).
slot(11).
slot(12).
slot(13).
slot(14).
slot(15).
slot(16).

demand(Time, DemandCount) :- 
    (Time = 9 -> DemandCount = 5;
     Time = 10 -> DemandCount = 10;
     Time = 11 -> DemandCount = 7;
     Time = 12 -> DemandCount = 8;
     Time = 13 -> DemandCount = 12;
     Time = 14 -> DemandCount = 1;
     Time = 15 -> DemandCount = 6;
     DemandCount = 3).

pricing(Service, Time, Price) :-
    base_price(Service, BasePrice),
    demand(Time, DemandCount),
    (DemandCount < 5 -> Price = BasePrice;
     DemandCount < 10 -> Price is BasePrice * 1.2;
     DemandCount < 15 -> Price is BasePrice * 1.5;
     Price is BasePrice * 2).

schedule_appointment(Time, Vet, Tech, Service) :-
    vet(Vet),
    tech(Tech),
    slot(Time),
    available_resources(Vet, Tech, Time),
    assertz(scheduled(Vet, Time, Service)),
    assertz(scheduled(Tech, Time, Service)),
    format('Scheduled appointment at ~w with ~w and ~w for ~w.~n', [Time, Vet, Tech, Service]).

available_resources(Vet, Tech, Time) :-
    \+ scheduled(Vet, Time, _),
    \+ scheduled(Tech, Time, _).

clear_schedules :- retractall(scheduled(_, _, _)).

main :- 
    clear_schedules,
    schedule_all,
    add_prices.

schedule_all :- 
    schedule_consultations,
    schedule_surgeries.

schedule_consultations :-
    findall(Time, (slot(Time), Time =< 30), TimeSlots),
    forall(member(Time, TimeSlots), (
        vet(Vet),
        tech(Tech),
        available_resources(Vet, Tech, Time),
        schedule_appointment(Time, Vet, Tech, consultation)
    )).

schedule_surgeries :-
    findall(Time, (slot(Time), Time > 30, Time =< 36), TimeSlots),
    forall(member(Time, TimeSlots), (
        vet(Vet),
        tech(Tech),
        available_resources(Vet, Tech, Time),
        schedule_appointment(Time, Vet, Tech, surgery)
    )).

add_prices :- 
    forall(scheduled(Vet, Time, Service), (
        pricing(Service, Time, Price),
        format('Price for appointment at ~w with ~w for ~w: $~w~n', [Time, Vet, Service, Price])
    )).

:- initialization(main).

