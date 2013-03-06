echo "Spawning $1 ethers"
for i in $(seq 1 $1);
do
    ./ether >/dev/null&
done
