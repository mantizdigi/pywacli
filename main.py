import typer

def main(name:str="Prem Raj" ,age:int =20):
    print(f"Hello {name}, you are {age} years old")


if __name__ =="__main__":
    typer.run(main)