import argparse
import hashlib
import multiprocessing
import os
import time
import string
import itertools


def parse_target_hash_file(target_hashes_file):
    target_hashes = []
    with open(target_hashes_file, 'r') as f:
        for line in f:
            line = line.strip()
            if len(line) == 32:
                algo = 'md5'
            elif len(line) == 40:
                algo = 'sha1'
            elif len(line) == 64:
                algo = 'sha256'
            elif len(line) == 128:
                algo = 'sha512'
            else:
                raise ValueError(f"Unknown hash type for hash value '{line}'")
            target_hashes.append((line, algo))
    return target_hashes

def crack_password(password, target_hash, algo):
    if algo == 'md5':
        hash_obj = hashlib.md5()
    elif algo == 'sha1':
        hash_obj = hashlib.sha1()
    elif algo == 'sha256':
        hash_obj = hashlib.sha256()
    elif algo == 'sha512':
        hash_obj = hashlib.sha512()
    else:
        raise ValueError(f"Unknown algorithm '{algo}'")
    hash_obj.update(password.encode('utf-8'))
    if hash_obj.hexdigest() == target_hash:
        return password
    return None

# def worker(wordlist, target_hash, algo, start_idx, end_idx, result_queue):
#     results = []
#     for i in range(start_idx, end_idx):
#         password = wordlist[i].strip()
#         solution = crack_password(password, target_hash, algo)
#         if solution:
#             results.append((target_hash, algo, solution))
#     result_queue.put(results)

def worker_wordlist(wordlist, target_hashes, algo, start_idx, end_idx, result_queue):
    results = []
    for i in range(start_idx, end_idx):
        password = wordlist[i].strip()
        for target_hash, algo in target_hashes:
            solution = crack_password(password, target_hash, algo)
            if solution:
                results.append((target_hash, algo, solution))
    result_queue.put(results)

def worker_brute_force(brute_force_passwords, target_hashes, algo, start_idx, end_idx, result_queue):
    results = []
    for i in range(start_idx, end_idx):
        password = brute_force_passwords[i]
        for target_hash, algo in target_hashes:
            solution = crack_password(password, target_hash, algo)
            if solution:
                results.append((target_hash, algo, solution))
    result_queue.put(results)

def crack_passwords(wordlist, target_hashes, algo, num_threads):
    results = multiprocessing.Queue()
    workers = []
    wordlist_size = len(wordlist)
    chunk_size = wordlist_size // num_threads
    for i in range(num_threads):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size
        if i == num_threads - 1:
            end_idx = wordlist_size
        worker_thread = multiprocessing.Process(target=worker_wordlist, args=(wordlist, target_hashes, algo, start_idx, end_idx, results))
        workers.append(worker_thread)
        worker_thread.start()

    results_list = []
    for worker_thread in workers:
        worker_thread.join()
        results_list += results.get()

    return results_list

def generate_passwords(length):
    # Generate all possible passwords of a certain length
    print("Brute Force list generating...")
    chars = string.ascii_letters + string.digits
    passwords = [''.join(i) for i in itertools.product(chars, repeat=length)]
    print("Brute Force list generated")
    return passwords

def brute_force_crack_passwords(brute_force_passwords, target_hashes, algo, num_threads):
    results = multiprocessing.Queue()
    workers = []
    wordlist_size = len(brute_force_passwords)
    chunk_size = wordlist_size // num_threads
    for i in range(num_threads):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size
        if i == num_threads - 1:
            end_idx = wordlist_size
        worker_thread = multiprocessing.Process(target=worker_brute_force, args=(brute_force_passwords, target_hashes, algo, start_idx, end_idx, results))
        workers.append(worker_thread)
        worker_thread.start()

    results_list = []
    for worker_thread in workers:
        worker_thread.join()
        results_list += results.get()

    return results_list


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--wordlist', help='Path to wordlist')
    parser.add_argument('-l', '--target_hashes', help='Path to file with target hashes')
    parser.add_argument('-t', '--threads', type=int, default=os.cpu_count(),
                        help='Number of threads to use (default: number of CPUs)')
    parser.add_argument('-bf', '--brute_force', type=int, default=3, help='Bruteforce password length')
    args = parser.parse_args()

    # Generate the wordlist or use the provided one
    if args.wordlist:
        with open(args.wordlist, 'r', encoding='utf-8', errors='ignore') as f:
            wordlist = f.readlines()
        wordlist = [password.strip() for password in wordlist]
    else:
        wordlist = []


    # with open(args.wordlist, 'r', encoding='utf-8', errors='ignore') as f:
    #     wordlist = f.readlines()

    target_hashes = parse_target_hash_file(args.target_hashes)

    total_count=len(target_hashes)
    num_cracked = 0

    start_time = time.time()
    
    # Crack passwords using the wordlist first
    for target_hash, algo in target_hashes:
        results = crack_passwords(wordlist, target_hashes, algo, args.threads)
    for result in results:
        print('{:<20} {:<10} {:<40}'.format(result[2], result[1], result[0]))
        num_cracked += 1
    
    # Generate the brute force password list if needed
    if args.brute_force:
        brute_force_passwords = generate_passwords(args.brute_force)
    else:
        brute_force_passwords = []
    

    # If there are still passwords left to crack, use the brute force method
    remaining_target_hashes = [(target_hash, algo) for target_hash, algo in target_hashes if not any(result[0] == target_hash and result[1] == algo for result in results)]
    if brute_force_passwords and remaining_target_hashes:

        brute_force_results = brute_force_crack_passwords(brute_force_passwords, remaining_target_hashes, algo, args.threads)
        for result in brute_force_results:
            print('{:<20} {:<10} {:<40}'.format(result[2], result[1], result[0]))
            num_cracked += 1

    end_time = time.time()   

    print("="*60)
    print(f"{num_cracked}/{total_count} passwords cracked")


    print(f"Time elapsed: {end_time - start_time:.2f} seconds")
