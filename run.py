import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
    from app.main import main
    raise SystemExit(main())
